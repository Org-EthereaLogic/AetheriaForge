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
    "evidence_dir", "/tmp/aetheriaforge_evidence", "Evidence output directory"
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

# MAGIC %md
# MAGIC ## Load Contract

# COMMAND ----------

from pathlib import Path

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

# COMMAND ----------

# MAGIC %md
# MAGIC ## Prepare Demo Data
# MAGIC
# MAGIC Replace this cell with your own data loading logic.
# MAGIC The demo creates a small synthetic dataset to prove the pipeline works.

# COMMAND ----------

import pandas as pd

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

forged_df = source_df.copy()
forged_df["amount"] = forged_df["amount"] * 1.1  # simulate a transformation

print(f"Source rows:  {len(source_df)}")
print(f"Forged rows:  {len(forged_df)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Pipeline

# COMMAND ----------

from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.orchestration.pipeline import ForgePipeline

writer = EvidenceWriter(Path(evidence_dir))
pipeline = ForgePipeline(contract, evidence_writer=writer)

result = pipeline.run(
    source_df=source_df,
    forged_df=forged_df,
    target_layer=target_layer,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline Result

# COMMAND ----------

print(f"Dataset:          {result.dataset_name}")
print(f"Pipeline verdict: {result.pipeline_verdict}")
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
