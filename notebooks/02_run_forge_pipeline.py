# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # AetheriaForge — Run Forge Pipeline
# MAGIC
# MAGIC Execute the full coherence-scored forge pipeline on a registered dataset.
# MAGIC
# MAGIC **Pipeline stages:**
# MAGIC 1. Schema enforcement against the contract
# MAGIC 2. Coherence-scored transformation (Shannon entropy)
# MAGIC 3. Entity resolution (if enabled in contract)
# MAGIC 4. Temporal reconciliation (if enabled in contract)
# MAGIC 5. Evidence writing (append-only artifact)

# COMMAND ----------

dbutils.widgets.text("catalog", "", "Unity Catalog catalog name")  # type: ignore[name-defined]
dbutils.widgets.text("schema", "default", "Unity Catalog schema name")  # type: ignore[name-defined]
dbutils.widgets.text(  # type: ignore[name-defined]
    "contract_path", "", "Path to forge contract YAML (leave blank for template)"
)
dbutils.widgets.text(  # type: ignore[name-defined]
    "evidence_dir", "", "Evidence output directory (leave blank for shared volume default)"
)
dbutils.widgets.text(  # type: ignore[name-defined]
    "target_layer", "silver", "Target Medallion layer (bronze, silver, gold)"
)

catalog = dbutils.widgets.get("catalog")  # type: ignore[name-defined]
schema = dbutils.widgets.get("schema")  # type: ignore[name-defined]
contract_path = dbutils.widgets.get("contract_path")  # type: ignore[name-defined]
evidence_dir = dbutils.widgets.get("evidence_dir")  # type: ignore[name-defined]
target_layer = dbutils.widgets.get("target_layer")  # type: ignore[name-defined]

# COMMAND ----------

import subprocess
import sys
from pathlib import Path


def _resolve_install_target() -> str:
    """Prefer the bundle-uploaded repo, then fall back to GitHub."""
    try:
        notebook_path = (
            dbutils.notebook.entry_point  # type: ignore[name-defined]
            .getDbutils()
            .notebook()
            .getContext()
            .notebookPath()
            .get()
        )
        workspace_path = Path("/Workspace") / notebook_path.lstrip("/")
        for parent in workspace_path.parents:
            if (
                (parent / "pyproject.toml").exists()
                and (parent / "src" / "aetheriaforge").exists()
            ):
                return str(parent)
    except Exception:
        pass
    return "git+https://github.com/Org-EthereaLogic/AetheriaForge.git"


try:
    from aetheriaforge.config.contract import ForgeContract
except ModuleNotFoundError:
    install_target = _resolve_install_target()
    print(f"Installing AetheriaForge package from: {install_target}")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", install_target]
    )
    from aetheriaforge.config.contract import ForgeContract

from aetheriaforge.runtime_paths import shared_evidence_dir


def _resolve_evidence_dir() -> Path:
    """Pick an explicit evidence dir or the shared Unity Catalog volume path."""
    if evidence_dir.strip():
        return Path(evidence_dir)
    if catalog.strip():
        return shared_evidence_dir(catalog, schema)
    return Path("/tmp/aetheriaforge_evidence")


resolved_evidence_dir = _resolve_evidence_dir()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Contract

# COMMAND ----------

from aetheriaforge.config.contract import ForgeContract
from aetheriaforge.paths import templates_dir

if contract_path:
    yaml_path = Path(contract_path)
else:
    yaml_path = templates_dir() / "forge_contract.yml"

contract = ForgeContract.from_yaml(yaml_path)
print(f"Contract loaded: {contract.dataset_name} v{contract.dataset_version}")
print(f"Target layer:    {target_layer}")
print(f"Threshold:       {contract.threshold_for_layer(target_layer)}")
print(f"Evidence dir:    {resolved_evidence_dir}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load Data
# MAGIC
# MAGIC The notebook loads real source data from the forge contract when a table or
# MAGIC file path is configured. Demo mode is only used when no real source surface
# MAGIC is configured.
# MAGIC **Demo runs are explicitly tagged in the evidence artifact and should not be
# MAGIC treated as production results.**

# COMMAND ----------

import json

import pandas as pd

from aetheriaforge.ingest import FileIngestor
from aetheriaforge.integration import (
    DriftIngester,
    FileEventChannel,
    discover_bundled_config,
)


def _surface_table_name(
    *,
    catalog_name: str,
    schema_name: str,
    table_name: str,
) -> str:
    if not table_name:
        msg = "Table name is required for table-backed execution"
        raise ValueError(msg)
    return ".".join(part for part in (catalog_name, schema_name, table_name) if part)


def _load_surface(
    *,
    label: str,
    table_name: str = "",
    path: str = "",
    file_format: str = "",
    options: dict[str, object] | None = None,
    catalog_name: str = "",
    schema_name: str = "",
) -> pd.DataFrame:
    if path:
        resolved_path = contract.resolve_relative_path(path)
        ingestor = FileIngestor()
        result = ingestor.ingest(
            resolved_path,
            file_format=file_format or None,
            options=dict(options or {}),
        )
        if not result.ok:
            msg = "; ".join(result.errors) or f"Failed to ingest {label}"
            raise RuntimeError(msg)
        print(f"Loaded {label} from file: {resolved_path} ({len(result.df)} rows)")
        return result.df

    if table_name:
        full_name = _surface_table_name(
            catalog_name=catalog_name,
            schema_name=schema_name,
            table_name=table_name,
        )
        frame = spark.table(full_name).toPandas()  # type: ignore[name-defined]
        print(f"Loaded {label} from Unity Catalog: {full_name} ({len(frame)} rows)")
        return frame

    msg = f"No {label} surface configured in the forge contract"
    raise ValueError(msg)


def _write_target_surface(df: pd.DataFrame) -> None:
    target_catalog = catalog.strip() or contract.target_catalog
    target_schema = schema.strip() or contract.target_schema
    if contract.target_table and target_catalog and target_schema:
        target_name = _surface_table_name(
            catalog_name=target_catalog,
            schema_name=target_schema,
            table_name=contract.target_table,
        )
        spark.createDataFrame(df).write.mode("overwrite").saveAsTable(target_name)  # type: ignore[name-defined]
        print(f"Wrote forged output to Unity Catalog: {target_name} ({len(df)} rows)")
        return

    if contract.target_path:
        target_path = contract.resolve_relative_path(contract.target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_format = (contract.target_format or target_path.suffix.lstrip(".")).lower()
        if target_format in {"parquet", "pq"}:
            df.to_parquet(target_path, index=False)
        elif target_format in {"json", "jsonl", "ndjson"}:
            lines = target_format in {"jsonl", "ndjson"}
            df.to_json(target_path, orient="records", lines=lines)
        elif target_format in {"csv", "tsv"}:
            separator = "\t" if target_format == "tsv" else ","
            df.to_csv(target_path, index=False, sep=separator)
        else:
            msg = f"Unsupported target file format '{target_format}'"
            raise ValueError(msg)
        print(f"Wrote forged output to file: {target_path} ({len(df)} rows)")
        return

    print("No target surface configured; forged output was computed but not written.")


def _load_secondary_df() -> pd.DataFrame | None:
    secondary = contract.resolution_secondary_source()
    if secondary is None:
        return None
    return _load_surface(
        label="secondary dataset",
        table_name=str(secondary.get("table", "")),
        path=str(secondary.get("path", "")),
        file_format=str(secondary.get("format", "")),
        options=dict(secondary.get("options", {})),
        catalog_name=str(
            secondary.get("catalog", catalog.strip() or contract.source_catalog)
        ),
        schema_name=str(
            secondary.get("schema", schema.strip() or contract.source_schema)
        ),
    )


def _resolve_event_channel():
    bundled_cfg = discover_bundled_config(contract_raw=contract.raw)
    if not bundled_cfg.enabled or not bundled_cfg.events_dir.strip():
        return None
    events_dir = contract.resolve_relative_path(bundled_cfg.events_dir)
    return FileEventChannel(events_dir)


_execution_mode: str

if contract.source_table and catalog.strip():
    source_catalog = catalog.strip() or contract.source_catalog
    source_schema = schema.strip() or contract.source_schema
    source_df = _load_surface(
        label="source dataset",
        table_name=contract.source_table,
        catalog_name=source_catalog,
        schema_name=source_schema,
    )
    _execution_mode = "contract_backed"
elif contract.source_table and contract.source_catalog and contract.source_schema:
    source_df = _load_surface(
        label="source dataset",
        table_name=contract.source_table,
        catalog_name=contract.source_catalog,
        schema_name=contract.source_schema,
    )
    _execution_mode = "contract_backed"
elif contract.source_path:
    source_df = _load_surface(
        label="source dataset",
        path=contract.source_path,
        file_format=contract.source_format,
        options=contract.source_options,
    )
    _execution_mode = "contract_backed"
else:
    print("WARNING: No source surface configured. Running in DEMO mode with synthetic data.")
    print("Evidence artifacts from this run will be tagged execution_mode='demo'.")
    print("These results do NOT reflect real data quality.\n")
    source_df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["alpha", "beta", "gamma", "delta", "epsilon"],
            "amount": [100.0, 200.0, 150.0, 300.0, 250.0],
            "event_date": pd.to_datetime(
                ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"]
            ),
            "updated_at": pd.Timestamp.now(),
        }
    )
    _execution_mode = "demo"

secondary_df = _load_secondary_df()

print(f"Source rows:     {len(source_df)}")
print(f"Execution mode:  {_execution_mode}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Pipeline

# COMMAND ----------

from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.orchestration.pipeline import ForgePipeline

writer = EvidenceWriter(resolved_evidence_dir)
event_channel = _resolve_event_channel()
pipeline = ForgePipeline(
    contract,
    evidence_writer=writer,
    event_channel=event_channel,
)

bundled_cfg = discover_bundled_config(contract_raw=contract.raw)
if bundled_cfg.enabled and bundled_cfg.auto_ingest and bundled_cfg.drift_dir.strip():
    drift_dir = contract.resolve_relative_path(bundled_cfg.drift_dir)
    registry = None
    from aetheriaforge.config.registry import DatasetRegistry

    registry = DatasetRegistry()
    registry.register(contract)
    actions = DriftIngester(
        drift_dir,
        registry,
        evidence_writer=writer,
    ).ingest_all()
    if actions:
        print("Drift follow-up actions:")
        for action in actions:
            print(
                f"  {action.dataset_name}: {action.action} "
                f"({action.drift_gate_verdict})"
            )

result = pipeline.run(
    source_df=source_df,
    secondary_df=secondary_df,
    target_layer=target_layer,
    execution_mode=_execution_mode,
    include_forged_df=True,
)

if result.pipeline_verdict == "FAIL":
    print("Target write blocked: pipeline verdict is FAIL.")
elif result.forged_df is not None:
    _write_target_surface(result.forged_df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Result

# COMMAND ----------

print(f"Dataset:          {result.dataset_name}")
print(f"Pipeline verdict: {result.pipeline_verdict}")
print(f"Execution mode:   {result.execution_mode}")
print(f"Source location:  {result.source_location}")
print(f"Contract version: {result.contract_version}")
print(f"Schema version:   {result.schema_version or '—'}")
print(f"Run at:           {result.run_at}")
print(f"Coherence score:  {result.forge_result.coherence_score:.6f}")
print(f"Threshold:        {result.forge_result.threshold}")
print(f"Forge verdict:    {result.forge_result.verdict}")
print(f"Records in:       {result.forge_result.records_in}")
print(f"Records out:      {result.forge_result.records_out}")
if result.forge_result.failure_reason:
    print(f"Failure reason:   {result.forge_result.failure_reason}")
print(f"Evidence path:    {result.evidence_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evidence Artifact

# COMMAND ----------

import json

print(json.dumps(result.as_dict(), indent=2, default=str))
