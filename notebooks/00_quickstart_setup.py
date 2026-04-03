# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # AetheriaForge — Quickstart Setup
# MAGIC
# MAGIC Install the AetheriaForge package and verify prerequisites.
# MAGIC
# MAGIC **What this notebook does:**
# MAGIC 1. Detect whether the package is available from the bundle deployment or GitHub
# MAGIC 2. Install the package into the notebook session
# MAGIC 3. Run a quick health check to prove the installation works

# COMMAND ----------

import subprocess
import sys
from pathlib import Path


def _resolve_install_target() -> str:
    """Resolve the install target: local bundle deployment first, then GitHub."""
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


install_target = _resolve_install_target()
print(f"Install target: {install_target}")

# COMMAND ----------

subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-q", install_target]
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Health Check

# COMMAND ----------

from aetheriaforge.config.contract import ForgeContract
from aetheriaforge.evidence.writer import EvidenceWriter
from aetheriaforge.forge.engine import ForgeEngine
from aetheriaforge.orchestration.pipeline import ForgePipeline

print("Import check: PASS")
print(f"  ForgeContract: {ForgeContract}")
print(f"  ForgeEngine:   {ForgeEngine}")
print(f"  ForgePipeline: {ForgePipeline}")
print(f"  EvidenceWriter: {EvidenceWriter}")

# COMMAND ----------

import pandas as pd

from aetheriaforge.forge.entropy import shannon_coherence_score

df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
score = shannon_coherence_score(df, df)
assert score >= 0.99, f"Self-coherence check failed: {score}"
print(f"Shannon coherence self-check: {score:.6f} (expected ~1.0)")
print("Quickstart: ALL CHECKS PASSED")
