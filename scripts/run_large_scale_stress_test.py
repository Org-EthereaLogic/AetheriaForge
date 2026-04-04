"""Large-scale stress test: real-world datasets through the full AetheriaForge pipeline.

Downloads are expected in data/raw/. Runs:
1. FileIngestor on all formats (CSV, Parquet, JSONL)
2. SchemaEnforcer with coercion
3. ForgeEngine coherence scoring
4. Full ForgePipeline orchestration
5. EntityResolver across two datasets
6. TemporalReconciler on time-series data
7. Evidence writing at every stage

Measures wall-clock time, memory, and records processed at each step.
"""

from __future__ import annotations

import sys
from pathlib import Path
from time import perf_counter
from typing import Any

import pandas as pd

from aetheriaforge.config.contract import ForgeContract
from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.forge.entropy import shannon_coherence_score
from aetheriaforge.ingest.reader import FileIngestor
from aetheriaforge.orchestration.pipeline import ForgePipeline
from aetheriaforge.resolution.policy import ResolutionPolicy
from aetheriaforge.schema.enforcer import ColumnSpec
from aetheriaforge.temporal.reconciler import TemporalConfig, TemporalReconciler

DATA_DIR = Path("data/raw")
EVIDENCE_DIR = Path("output/stress-test/evidence")
CONTRACTS_DIR = Path("output/stress-test/contracts")


# -- Contracts ---------------------------------------------------------------

def _make_contract(name: str, version: str = "1.0.0", **overrides: Any) -> ForgeContract:
    base: dict[str, Any] = {
        "dataset": {"name": name, "version": version},
        "source": {"catalog": "stress", "schema": "bronze", "table": name},
        "target": {"catalog": "stress", "schema": "silver", "table": f"{name}_forged"},
        "coherence": {"engine": "shannon", "thresholds": {"bronze_min": 0.3, "silver_min": 0.7, "gold_min": 0.95}},
        "schema_contract": {"enforce": True, "evolution": "versioned", "coerce_types": True},
        "resolution": {"enabled": False},
        "temporal": {"enabled": False},
    }
    base.update(overrides)
    return ForgeContract.from_dict(base)


# -- Timing helpers ----------------------------------------------------------

class Timer:
    """Lightweight timer using process RSS delta instead of tracemalloc.

    tracemalloc adds 5-10x overhead on allocation-heavy workloads (e.g.
    string conversion of large object columns).  Process RSS is coarser
    but free.
    """
    def __init__(self, label: str) -> None:
        self.label = label
        self.elapsed = 0.0
        self.mem_peak_mb = 0.0

    def __enter__(self) -> "Timer":
        import resource
        self._rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        self._t0 = perf_counter()
        return self

    def __exit__(self, *_: Any) -> None:
        import resource
        self.elapsed = perf_counter() - self._t0
        rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # macOS reports bytes, Linux reports KB
        divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
        self.mem_peak_mb = max(0, (rss_after - self._rss_before)) / divisor

    def report(self) -> str:
        return f"  [{self.label}] {self.elapsed:.3f}s | mem delta: {self.mem_peak_mb:.1f} MB"


results: list[dict[str, Any]] = []


def record(
    stage: str, dataset: str, rows: int, cols: int,
    elapsed: float, mem_mb: float,
    verdict: str = "", extra: str = "",
) -> None:
    entry = {
        "stage": stage, "dataset": dataset, "rows": rows, "cols": cols,
        "time_s": round(elapsed, 3), "mem_mb": round(mem_mb, 1),
        "verdict": verdict, "extra": extra,
    }
    results.append(entry)
    parts = [
        f"  {stage:<30s} | {dataset:<25s} | {rows:>10,} rows"
        f" | {cols:>3} cols | {elapsed:>7.3f}s | {mem_mb:>7.1f} MB"
    ]
    if verdict:
        parts.append(f" | {verdict}")
    if extra:
        parts.append(f" | {extra}")
    print("".join(parts))


def _forge_dataset(name: str, df: pd.DataFrame) -> pd.DataFrame:
    """Create a realistic forged version of a dataset by applying filtering."""
    if name.startswith("yellow_taxi"):
        return df.dropna(subset=["passenger_count"]).reset_index(drop=True)
    elif name == "us_counties_covid":
        return df[df["cases"] > 0].reset_index(drop=True)
    elif name.startswith("earthquakes"):
        if "mag" in df.columns:
            return df[df["mag"] >= 3.0].reset_index(drop=True)
        return df.dropna().reset_index(drop=True)
    elif name in ("air_quality", "epa_aqi_2024"):
        return df.dropna(subset=[df.columns[0]]).reset_index(drop=True)
    elif name == "github_events":
        return df.dropna(subset=["org"]).reset_index(drop=True)
    return df.copy()


# -- Main test ---------------------------------------------------------------

def main() -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    writer = EvidenceWriter(EVIDENCE_DIR)

    print("=" * 120)
    print("AetheriaForge Large-Scale Stress Test")
    print("=" * 120)

    # ========================================================================
    # PHASE 1: Ingest all datasets via FileIngestor
    # ========================================================================
    print("\n--- PHASE 1: File Ingestion ---")
    ingestor = FileIngestor(evidence_writer=writer)
    dataframes: dict[str, pd.DataFrame] = {}

    ingest_targets = [
        ("yellow_taxi_jan", DATA_DIR / "yellow_tripdata_2024-01.parquet"),
        ("yellow_taxi_jun", DATA_DIR / "yellow_tripdata_2024-06.parquet"),
        ("yellow_taxi_oct", DATA_DIR / "yellow_tripdata_2024-10.parquet"),
        ("us_counties_covid", DATA_DIR / "us-counties.csv"),
        ("earthquakes", DATA_DIR / "earthquakes_all.csv"),
        ("earthquakes_30day", DATA_DIR / "earthquakes_30day.csv"),
        ("air_quality", DATA_DIR / "air_quality.csv"),
        ("epa_aqi_2024", DATA_DIR / "daily_aqi_by_county_2024.csv"),
        ("github_events", DATA_DIR / "github_events.json"),
    ]

    for name, path in ingest_targets:
        fmt = None
        opts: dict[str, Any] = {}
        if name == "github_events":
            fmt = "jsonl"

        with Timer(f"ingest_{name}") as t:
            result = ingestor.ingest(path, file_format=fmt, options=opts)

        if result.errors:
            print(f"  INGEST ERROR for {name}: {result.errors}")
            continue

        dataframes[name] = result.df
        record("ingest", name, result.records_read, len(result.columns), t.elapsed, t.mem_peak_mb,
               extra=f"size={path.stat().st_size / 1024**2:.1f}MB")

    # ========================================================================
    # PHASE 2: Raw entropy scoring (benchmark the core algorithm)
    # ========================================================================
    print("\n--- PHASE 2: Raw Shannon Entropy Scoring (benchmarks) ---")

    for name, df in dataframes.items():
        forged = _forge_dataset(name, df)

        with Timer(f"entropy_{name}") as t:
            score = shannon_coherence_score(df, forged)

        record("entropy_score", name, len(df), len(df.columns), t.elapsed, t.mem_peak_mb,
               verdict=f"score={score:.6f}", extra=f"forged={len(forged):,}")

    # ========================================================================
    # PHASE 3: Full ForgePipeline with schema enforcement
    # ========================================================================
    print("\n--- PHASE 3: Full Forge Pipeline ---")

    for name, df in dataframes.items():
        contract = _make_contract(name)

        # Build schema columns from the actual data
        schema_cols = [
            ColumnSpec(name=col, dtype=str(df[col].dtype), nullable=True)
            for col in df.columns
        ]

        forged = _forge_dataset(name, df)

        pipeline = ForgePipeline(contract, evidence_writer=writer)

        with Timer(f"pipeline_{name}") as t:
            pipe_result = pipeline.run(
                source_df=df,
                forged_df=forged,
                schema_columns=schema_cols,
                target_layer="silver",
                execution_mode="contract_backed",
            )

        record("full_pipeline", name, len(df), len(df.columns), t.elapsed, t.mem_peak_mb,
               verdict=pipe_result.pipeline_verdict,
               extra=f"coherence={pipe_result.forge_result.coherence_score:.6f}")

    # ========================================================================
    # PHASE 4: Entity Resolution (earthquake locations vs air quality locations)
    # ========================================================================
    print("\n--- PHASE 4: Entity Resolution ---")

    if "earthquakes" in dataframes and "air_quality" in dataframes:
        eq_df = dataframes["earthquakes"].copy()
        aq_df = dataframes["air_quality"].copy()

        # Prepare: use 'place' from earthquakes and 'Name' from air quality
        # as approximate key columns for resolution testing
        if "place" in eq_df.columns and "Name" in aq_df.columns:
            eq_sample = eq_df.head(5000).copy()
            aq_sample = aq_df.head(5000).copy()

            # Normalize column names for resolution
            eq_sample = eq_sample.rename(columns={"place": "location"})
            aq_sample = aq_sample.rename(columns={"Name": "location"})

            policy = ResolutionPolicy.from_dict({
                "policy": {"name": "stress_test_resolution", "version": "1.0.0"},
                "sources": [
                    {"name": "earthquakes", "key_columns": ["location"]},
                    {"name": "air_quality", "key_columns": ["location"]},
                ],
                "matching": {"strategy": "exact", "ambiguity_behavior": "skip"},
                "evidence": {"record_all_decisions": True, "include_rejected_matches": True},
            })

            from aetheriaforge.resolution.resolver import EntityResolver
            resolver = EntityResolver(policy, evidence_writer=writer)

            with Timer("resolve_eq_aq") as t:
                res_result = resolver.resolve(eq_sample, aq_sample)

            record(
                "entity_resolution", "earthquakes_x_air_quality",
                len(eq_sample) + len(aq_sample), 0, t.elapsed, t.mem_peak_mb,
                extra=(
                    f"resolved={res_result.resolved_count}"
                    f" unresolved={res_result.unresolved_count}"
                    f" ambiguous={res_result.ambiguous_count}"
                ),
            )

    # ========================================================================
    # PHASE 5: Temporal Reconciliation on COVID data and EPA AQI
    # ========================================================================
    print("\n--- PHASE 5: Temporal Reconciliation ---")

    if "us_counties_covid" in dataframes:
        covid_df = dataframes["us_counties_covid"].copy()

        if "state" in covid_df.columns and "date" in covid_df.columns:
            # Test 1: New York subset
            state_subset = covid_df[covid_df["state"] == "New York"].copy()
            state_subset["date"] = pd.to_datetime(state_subset["date"])

            temporal_config = TemporalConfig(
                timestamp_column="date",
                merge_strategy="latest_wins",
                conflict_behavior="skip",
                entity_key_columns=("county", "state") if "county" in state_subset.columns else ("fips",),
            )

            reconciler = TemporalReconciler(temporal_config, evidence_writer=writer)

            with Timer("temporal_covid_ny") as t:
                temp_result = reconciler.reconcile(state_subset)

            record("temporal_reconcile", "covid_new_york",
                   len(state_subset), len(state_subset.columns), t.elapsed, t.mem_peak_mb,
                   extra=f"reconciled={temp_result.reconciled_count} conflicts={temp_result.conflict_count}")

            # Test 2: California (larger subset)
            ca_subset = covid_df[covid_df["state"] == "California"].copy()
            ca_subset["date"] = pd.to_datetime(ca_subset["date"])

            reconciler2 = TemporalReconciler(temporal_config, evidence_writer=writer)

            with Timer("temporal_covid_ca") as t:
                temp_result2 = reconciler2.reconcile(ca_subset)

            record("temporal_reconcile", "covid_california",
                   len(ca_subset), len(ca_subset.columns), t.elapsed, t.mem_peak_mb,
                   extra=f"reconciled={temp_result2.reconciled_count} conflicts={temp_result2.conflict_count}")

    if "epa_aqi_2024" in dataframes:
        epa_df = dataframes["epa_aqi_2024"].copy()
        date_col = None
        for c in epa_df.columns:
            if "date" in c.lower():
                date_col = c
                break
        county_col = None
        for c in epa_df.columns:
            if "county" in c.lower():
                county_col = c
                break
        state_col = None
        for c in epa_df.columns:
            if "state" in c.lower() and "code" not in c.lower():
                state_col = c
                break

        if date_col and county_col and state_col:
            epa_df[date_col] = pd.to_datetime(epa_df[date_col])

            temporal_config_epa = TemporalConfig(
                timestamp_column=date_col,
                merge_strategy="latest_wins",
                conflict_behavior="skip",
                entity_key_columns=(county_col, state_col),
            )

            reconciler3 = TemporalReconciler(temporal_config_epa, evidence_writer=writer)

            with Timer("temporal_epa_aqi") as t:
                temp_result3 = reconciler3.reconcile(epa_df)

            record("temporal_reconcile", "epa_aqi_2024",
                   len(epa_df), len(epa_df.columns), t.elapsed, t.mem_peak_mb,
                   extra=f"reconciled={temp_result3.reconciled_count} conflicts={temp_result3.conflict_count}")

    # ========================================================================
    # PHASE 6: Stress the evidence directory (write + read many artifacts)
    # ========================================================================
    print("\n--- PHASE 6: Evidence System Stress ---")

    # Count how many evidence files we generated
    evidence_files = list(EVIDENCE_DIR.glob("*.json"))
    print(f"  Evidence files written: {len(evidence_files)}")

    # Benchmark reading them all back via TransformationHistory
    from aetheriaforge.evidence.history import TransformationHistory
    history = TransformationHistory(EVIDENCE_DIR)

    with Timer("history_list_all") as t:
        all_records = history.list_all()
    record("evidence_list_all", "all_datasets", len(all_records), 0, t.elapsed, t.mem_peak_mb)

    with Timer("history_query_pass") as t:
        pass_records = history.query(verdict="PASS")
    record("evidence_query_pass", "all_datasets", len(pass_records), 0, t.elapsed, t.mem_peak_mb)

    with Timer("history_summary") as t:
        summary = history.summary()
    record("evidence_summary", "all_datasets", len(all_records), 0, t.elapsed, t.mem_peak_mb)
    for ds, counts in summary.items():
        print(f"    {ds}: {counts}")

    # ========================================================================
    # PHASE 7: Write forge contracts for app testing
    # ========================================================================
    print("\n--- PHASE 7: Writing Forge Contracts for App ---")
    import yaml

    for name in dataframes:
        contract = _make_contract(name)
        contract_path = CONTRACTS_DIR / f"{name}.yml"
        src_loc = {
            "catalog": contract.source_catalog,
            "schema": contract.source_schema, "table": contract.source_table,
        }
        tgt_loc = {
            "catalog": contract.target_catalog,
            "schema": contract.target_schema, "table": contract.target_table,
        }
        contract_data = {
            "dataset": {"name": contract.dataset_name, "version": contract.dataset_version},
            "source": src_loc,
            "target": tgt_loc,
            "coherence": {"engine": contract.coherence.engine, "thresholds": {
                "bronze_min": contract.coherence.bronze_min,
                "silver_min": contract.coherence.silver_min,
                "gold_min": contract.coherence.gold_min,
            }},
            "schema_contract": {
                "enforce": True, "evolution": "versioned", "coerce_types": True,
            },
        }
        contract_path.write_text(yaml.dump(contract_data, default_flow_style=False))
        print(f"  Wrote {contract_path}")

    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "=" * 120)
    print("STRESS TEST SUMMARY")
    print("=" * 120)
    hdr = (
        f"{'Stage':<30s} | {'Dataset':<25s} | {'Rows':>10s}"
        f" | {'Cols':>4s} | {'Time':>8s} | {'Mem MB':>8s}"
        f" | {'Verdict':<10s} | Extra"
    )
    print(hdr)
    print("-" * 120)
    for r in results:
        line = (
            f"{r['stage']:<30s} | {r['dataset']:<25s}"
            f" | {r['rows']:>10,} | {r['cols']:>4}"
            f" | {r['time_s']:>7.3f}s | {r['mem_mb']:>7.1f} "
            f" | {r['verdict']:<10s} | {r['extra']}"
        )
        print(line)
    print("=" * 120)
    print(f"Total evidence files: {len(list(EVIDENCE_DIR.glob('*.json')))}")
    print(f"Evidence directory: {EVIDENCE_DIR.resolve()}")
    print(f"Contracts directory: {CONTRACTS_DIR.resolve()}")


if __name__ == "__main__":
    main()
