"""Generate real-world stress fixtures for the AetheriaForge operator app.

The script streams several large public datasets from official portals, writes
forge contracts, runs the local pipeline against chunked real data, and emits
append-only evidence artifacts plus a manifest that records exactly what was
generated.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from io import TextIOWrapper
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.request import urlopen

import pandas as pd
import yaml

from aetheriaforge.config.contract import ForgeContract
from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.orchestration.pipeline import ForgePipeline
from aetheriaforge.resolution.policy import ResolutionPolicy
from aetheriaforge.schema.enforcer import ColumnSpec
from aetheriaforge.temporal.reconciler import TemporalConfig


@dataclass(frozen=True)
class DatasetSpec:
    """Configuration for one public dataset used in the stress run."""

    name: str
    version: str
    catalog_url: str
    source_url: str
    usecols: tuple[str, ...]
    key_column: str
    timestamp_column: str
    temporal_entity_column: str
    secondary_columns: tuple[str, ...]
    source_schema: str
    source_table: str
    target_schema: str
    target_table: str


DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        name="chicago_crimes",
        version="2026.04.0",
        catalog_url="https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2",
        source_url="https://data.cityofchicago.org/api/views/ijzp-q8t2/rows.csv?accessType=DOWNLOAD",
        usecols=(
            "ID",
            "Case Number",
            "Date",
            "Primary Type",
            "Arrest",
            "Community Area",
            "Description",
        ),
        key_column="id",
        timestamp_column="date",
        temporal_entity_column="community_area",
        secondary_columns=("id", "primary_type", "description"),
        source_schema="public_safety",
        source_table="crimes_2001_to_present",
        target_schema="silver",
        target_table="crimes_forged",
    ),
    DatasetSpec(
        name="nyc_311_requests",
        version="2026.04.0",
        catalog_url="https://data.cityofnewyork.us/Social-Services/311-Service-Requests-from-2020-to-Present/erm2-nwe9",
        source_url="https://data.cityofnewyork.us/api/views/erm2-nwe9/rows.csv?accessType=DOWNLOAD",
        usecols=(
            "Unique Key",
            "Created Date",
            "Agency",
            "Agency Name",
            "Problem (formerly Complaint Type)",
            "Status",
            "Borough",
        ),
        key_column="unique_key",
        timestamp_column="created_date",
        temporal_entity_column="borough",
        secondary_columns=("unique_key", "agency", "agency_name"),
        source_schema="service_ops",
        source_table="service_requests_2020_present",
        target_schema="silver",
        target_table="service_requests_forged",
    ),
    DatasetSpec(
        name="nyc_motor_vehicle_collisions",
        version="2026.04.0",
        catalog_url="https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95",
        source_url="https://data.cityofnewyork.us/api/views/h9gi-nx95/rows.csv?accessType=DOWNLOAD",
        usecols=(
            "CRASH DATE",
            "BOROUGH",
            "ZIP CODE",
            "NUMBER OF PERSONS INJURED",
            "CONTRIBUTING FACTOR VEHICLE 1",
            "COLLISION_ID",
            "VEHICLE TYPE CODE 1",
        ),
        key_column="collision_id",
        timestamp_column="crash_date",
        temporal_entity_column="borough",
        secondary_columns=("collision_id", "zip_code", "vehicle_type_code_1"),
        source_schema="transportation",
        source_table="motor_vehicle_collisions",
        target_schema="silver",
        target_table="motor_vehicle_collisions_forged",
    ),
)

PROFILES: tuple[str, ...] = ("pass", "warn", "fail")


def _snake_case(raw: str) -> str:
    """Convert a column header into a stable snake_case identifier."""
    slug = raw.strip().lower()
    for token in ("(", ")", "/", "-", ".", ","):
        slug = slug.replace(token, " ")
    slug = "_".join(part for part in slug.split() if part)
    return slug


def _contract_payload(spec: DatasetSpec, silver_min: float) -> dict[str, Any]:
    """Return a forge contract payload for a dataset."""
    return {
        "dataset": {"name": spec.name, "version": spec.version},
        "source": {
            "catalog": "public",
            "schema": spec.source_schema,
            "table": spec.source_table,
        },
        "target": {
            "catalog": "public",
            "schema": spec.target_schema,
            "table": spec.target_table,
        },
        "coherence": {
            "engine": "shannon",
            "thresholds": {
                "bronze_min": 0.60,
                "silver_min": silver_min,
                "gold_min": 0.95,
            },
        },
        "schema_contract": {
            "enforce": True,
            "evolution": "versioned",
            "coerce_types": True,
        },
        "resolution": {"enabled": True},
        "temporal": {"enabled": True},
        "metadata": {
            "stress_source_catalog_url": spec.catalog_url,
            "stress_source_download_url": spec.source_url,
        },
    }


def _write_contract(contracts_dir: Path, spec: DatasetSpec, silver_min: float) -> Path:
    """Write a dataset contract YAML and return its path."""
    contracts_dir.mkdir(parents=True, exist_ok=True)
    path = contracts_dir / f"{spec.name}.yml"
    path.write_text(yaml.safe_dump(_contract_payload(spec, silver_min), sort_keys=False))
    return path


def _schema_columns(df: pd.DataFrame, spec: DatasetSpec) -> list[ColumnSpec]:
    """Build a minimal schema contract for enforcement."""
    return [
        ColumnSpec(name=spec.key_column, dtype=str(df[spec.key_column].dtype), nullable=False),
        ColumnSpec(name=spec.timestamp_column, dtype=str(df[spec.timestamp_column].dtype), nullable=True),
        ColumnSpec(
            name=spec.temporal_entity_column,
            dtype=str(df[spec.temporal_entity_column].dtype),
            nullable=True,
        ),
    ]


def _resolution_policy(spec: DatasetSpec) -> ResolutionPolicy:
    """Return an exact-match resolution policy for the dataset."""
    return ResolutionPolicy.from_dict(
        {
            "policy": {"name": f"{spec.name}_policy", "version": spec.version},
            "sources": [
                {"name": "primary", "key_columns": [spec.key_column], "priority": 1},
                {"name": "secondary", "key_columns": [spec.key_column], "priority": 2},
            ],
            "matching": {
                "strategy": "exact",
                "confidence_threshold": 1.0,
                "ambiguity_behavior": "skip",
            },
            "evidence": {
                "record_all_decisions": True,
                "include_rejected_matches": True,
            },
        }
    )


def _temporal_config(spec: DatasetSpec) -> TemporalConfig:
    """Return a stable latest-wins temporal config for the dataset."""
    return TemporalConfig(
        timestamp_column=spec.timestamp_column,
        merge_strategy="latest_wins",
        conflict_behavior="keep_first",
        entity_key_columns=(spec.temporal_entity_column,),
    )


def _normalize_chunk(chunk: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
    """Keep the configured columns and normalize them into a clean chunk."""
    renamed = chunk.rename(columns={col: _snake_case(col) for col in chunk.columns})
    normalized = renamed.copy()

    for column in normalized.columns:
        if normalized[column].dtype == object:
            normalized[column] = normalized[column].astype("string").str.strip()

    normalized[spec.key_column] = normalized[spec.key_column].astype("string")
    normalized[spec.timestamp_column] = pd.to_datetime(
        normalized[spec.timestamp_column],
        format="mixed",
        utc=True,
        errors="coerce",
    )
    normalized[spec.temporal_entity_column] = (
        normalized[spec.temporal_entity_column]
        .astype("string")
        .fillna("UNKNOWN")
    )

    normalized = normalized.dropna(
        subset=[spec.key_column, spec.timestamp_column]
    ).reset_index(drop=True)

    return normalized


def _with_temporal_conflict(df: pd.DataFrame, spec: DatasetSpec) -> pd.DataFrame:
    """Append a duplicate-timestamp row to exercise temporal conflict reporting."""
    if len(df) < 2:
        return df
    duplicate = df.iloc[[0]].copy()
    duplicate[spec.temporal_entity_column] = df.iloc[1][spec.temporal_entity_column]
    duplicate[spec.timestamp_column] = df.iloc[1][spec.timestamp_column]
    return pd.concat([df, duplicate], ignore_index=True)


def _build_profile_inputs(
    base_chunk: pd.DataFrame,
    spec: DatasetSpec,
    profile: str,
    detailed: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, list[ColumnSpec], pd.DataFrame | None]:
    """Build source/forged inputs for a stress-test profile."""
    source_df = base_chunk.copy().reset_index(drop=True)

    if detailed:
        source_df = _with_temporal_conflict(source_df, spec)

    if profile == "pass":
        forged_df = source_df.copy()
    elif profile == "warn":
        warned_source = source_df.copy()
        n_bad = max(1, math.ceil(len(warned_source) * 0.05))
        warned_source.loc[warned_source.index[:n_bad], spec.key_column] = pd.NA
        source_df = warned_source
        forged_df = warned_source.dropna(subset=[spec.key_column]).reset_index(drop=True)
    elif profile == "fail":
        forged_df = pd.DataFrame(
            {
                "dataset_bucket": [spec.name],
                "records_in": [len(source_df)],
                "generated_at": [datetime.now(tz=timezone.utc).isoformat()],
            }
        )
    else:
        msg = f"Unsupported profile: {profile}"
        raise ValueError(msg)

    schema_columns = _schema_columns(source_df, spec)
    secondary_df = None

    if detailed and profile != "fail":
        secondary_df = (
            forged_df[list(spec.secondary_columns)]
            .dropna(subset=[spec.key_column])
            .drop_duplicates(subset=[spec.key_column])
            .reset_index(drop=True)
        )

    return source_df, forged_df, schema_columns, secondary_df


def _iter_dataset_chunks(
    spec: DatasetSpec,
    *,
    chunk_size: int,
    max_chunks: int,
) -> Iterator[pd.DataFrame]:
    """Yield up to ``max_chunks`` clean chunks from the dataset source."""
    emitted = 0
    with urlopen(spec.source_url) as response:
        reader = csv.DictReader(
            TextIOWrapper(response, encoding="utf-8", errors="replace")
        )
        rows: list[dict[str, str | None]] = []

        for row in reader:
            rows.append({column: row.get(column) for column in spec.usecols})

            if len(rows) < chunk_size:
                continue

            normalized = _normalize_chunk(pd.DataFrame.from_records(rows), spec)
            rows = []
            if normalized.empty:
                continue
            yield normalized
            emitted += 1
            if emitted >= max_chunks:
                break

        if rows and emitted < max_chunks:
            normalized = _normalize_chunk(pd.DataFrame.from_records(rows), spec)
            if not normalized.empty:
                yield normalized


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        default="output/real-data-stress",
        help="Parent directory for the timestamped fixture run.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Rows per streamed chunk from each dataset.",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=112,
        help="Maximum clean chunks to use from each dataset.",
    )
    parser.add_argument(
        "--detailed-every",
        type=int,
        default=16,
        help="Enable resolution and temporal stages every N chunks.",
    )
    parser.add_argument(
        "--silver-min",
        type=float,
        default=0.85,
        help="Silver-layer coherence threshold written into generated contracts.",
    )
    return parser.parse_args()


def main() -> int:
    """Generate the contracts, evidence artifacts, and manifest."""
    args = _parse_args()
    run_id = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = Path(args.output_root) / run_id
    contracts_dir = output_root / "contracts"
    evidence_dir = output_root / "evidence"
    manifest_path = output_root / "manifest.json"

    output_root.mkdir(parents=True, exist_ok=True)
    writer = EvidenceWriter(evidence_dir)

    dataset_summaries: list[dict[str, Any]] = []
    total_artifacts = 0
    started_at = perf_counter()

    for spec in DATASETS:
        contract_path = _write_contract(contracts_dir, spec, args.silver_min)
        contract = ForgeContract.from_yaml(contract_path)
        pipeline = ForgePipeline(contract, evidence_writer=writer)
        resolution_policy = _resolution_policy(spec)
        temporal_config = _temporal_config(spec)

        verdict_counts = {label: 0 for label in ("PASS", "WARN", "FAIL")}
        processed_rows = 0
        detailed_runs = 0
        chunks_used = 0

        # Process each streamed chunk immediately so the first evidence artifacts
        # appear as soon as the remote source yields enough rows.
        for chunk_index, base_chunk in enumerate(
            _iter_dataset_chunks(
                spec,
                chunk_size=args.chunk_size,
                max_chunks=args.max_chunks,
            ),
            start=1,
        ):
            chunks_used = chunk_index
            processed_rows += len(base_chunk)
            detailed = args.detailed_every > 0 and chunk_index % args.detailed_every == 0

            for profile in PROFILES:
                source_df, forged_df, schema_columns, secondary_df = _build_profile_inputs(
                    base_chunk=base_chunk,
                    spec=spec,
                    profile=profile,
                    detailed=detailed,
                )
                result = pipeline.run(
                    source_df=source_df,
                    forged_df=forged_df,
                    schema_columns=schema_columns,
                    secondary_df=secondary_df if detailed and profile != "fail" else None,
                    resolution_policy=resolution_policy if detailed and profile != "fail" else None,
                    temporal_config=temporal_config if detailed and profile != "fail" else None,
                    target_layer="silver",
                )
                verdict_counts[result.pipeline_verdict] = verdict_counts.get(result.pipeline_verdict, 0) + 1
                total_artifacts += 1
                if detailed and profile != "fail":
                    detailed_runs += 1

        dataset_summaries.append(
            {
                "name": spec.name,
                "catalog_url": spec.catalog_url,
                "source_url": spec.source_url,
                "contract_path": str(contract_path),
                "chunks_used": chunks_used,
                "chunk_size": args.chunk_size,
                "rows_processed": processed_rows,
                "artifact_count": sum(verdict_counts.values()),
                "verdict_counts": verdict_counts,
                "detailed_runs": detailed_runs,
            }
        )

    manifest = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "output_root": str(output_root),
        "contracts_dir": str(contracts_dir),
        "evidence_dir": str(evidence_dir),
        "artifact_profiles": list(PROFILES),
        "datasets": dataset_summaries,
        "total_artifacts": total_artifacts,
        "generation_seconds": round(perf_counter() - started_at, 3),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
