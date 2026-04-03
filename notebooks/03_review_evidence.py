# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # AetheriaForge — Review Evidence
# MAGIC
# MAGIC Inspect transformation evidence artifacts written by the forge pipeline.
# MAGIC
# MAGIC **What this notebook does:**
# MAGIC 1. List all evidence artifacts in the configured directory
# MAGIC 2. Display summary statistics (verdicts, scores, timestamps)
# MAGIC 3. Allow inspection of individual evidence files

# COMMAND ----------

dbutils.widgets.text(  # type: ignore[name-defined]
    "evidence_dir", "/tmp/aetheriaforge_evidence", "Evidence directory"
)

evidence_dir = dbutils.widgets.get("evidence_dir")  # type: ignore[name-defined]

# COMMAND ----------

import json
from pathlib import Path

evidence_path = Path(evidence_dir)

if not evidence_path.exists():
    print(f"Evidence directory does not exist: {evidence_path}")
    dbutils.notebook.exit("NO_EVIDENCE_DIR")  # type: ignore[name-defined]

files = sorted(evidence_path.glob("forge-evidence-*.json"))
print(f"Found {len(files)} evidence artifact(s) in {evidence_path}")

if not files:
    dbutils.notebook.exit("NO_ARTIFACTS")  # type: ignore[name-defined]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Evidence Summary

# COMMAND ----------

import pandas as pd

records = []
for f in files:
    artifact = json.loads(f.read_text())
    forge = artifact.get("forge_result", {})
    records.append(
        {
            "file": f.name,
            "event": artifact.get("event", "unknown"),
            "dataset": artifact.get("dataset_name", forge.get("dataset_name", "")),
            "verdict": artifact.get("pipeline_verdict", forge.get("verdict", "")),
            "coherence_score": forge.get("coherence_score"),
            "threshold": forge.get("threshold"),
            "records_in": forge.get("records_in"),
            "records_out": forge.get("records_out"),
            "run_at": artifact.get("run_at", forge.get("forged_at", "")),
        }
    )

summary_df = pd.DataFrame(records)
display(summary_df)  # type: ignore[name-defined]

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verdict Distribution

# COMMAND ----------

if "verdict" in summary_df.columns:
    counts = summary_df["verdict"].value_counts()
    for verdict, count in counts.items():
        print(f"  {verdict}: {count}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Inspect Latest Artifact

# COMMAND ----------

latest = files[-1]
artifact = json.loads(latest.read_text())
print(f"Latest artifact: {latest.name}\n")
print(json.dumps(artifact, indent=2, default=str))
