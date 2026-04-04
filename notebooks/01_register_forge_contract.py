# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # AetheriaForge — Register Forge Contract
# MAGIC
# MAGIC Load and validate a forge contract from a YAML file.
# MAGIC
# MAGIC **What this notebook does:**
# MAGIC 1. Read a forge contract YAML from the bundle templates or a custom path
# MAGIC 2. Parse and validate the contract structure
# MAGIC 3. Display the resolved contract configuration

# COMMAND ----------

dbutils.widgets.text("catalog", "", "Unity Catalog catalog name")  # type: ignore[name-defined]
dbutils.widgets.text("schema", "default", "Unity Catalog schema name")  # type: ignore[name-defined]
dbutils.widgets.text(  # type: ignore[name-defined]
    "contract_path", "", "Path to forge contract YAML (leave blank for template)"
)
dbutils.widgets.text(  # type: ignore[name-defined]
    "contracts_dir", "", "Contract registry directory (leave blank for shared volume default)"
)

catalog = dbutils.widgets.get("catalog")  # type: ignore[name-defined]
schema = dbutils.widgets.get("schema")  # type: ignore[name-defined]
contract_path = dbutils.widgets.get("contract_path")  # type: ignore[name-defined]
contracts_dir = dbutils.widgets.get("contracts_dir")  # type: ignore[name-defined]

# COMMAND ----------

import subprocess
import sys
import json
from pathlib import Path

import yaml


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

from aetheriaforge.paths import templates_dir
from aetheriaforge.runtime_paths import shared_contracts_dir


def _resolve_registry_dir() -> Path:
    """Pick an explicit registry dir or the shared Unity Catalog volume path."""
    if contracts_dir.strip():
        return Path(contracts_dir)
    if catalog.strip():
        return shared_contracts_dir(catalog, schema)
    return Path("/tmp/aetheriaforge_contracts")

if contract_path:
    yaml_path = Path(contract_path)
else:
    yaml_path = templates_dir() / "forge_contract.yml"

print(f"Loading forge contract from: {yaml_path}")
contract = ForgeContract.from_yaml(yaml_path)

registry_dir = _resolve_registry_dir()
registry_dir.mkdir(parents=True, exist_ok=True)
registered_path = registry_dir / f"{contract.dataset_name}.yml"
registered_path.write_text(yaml.safe_dump(contract.raw, sort_keys=False))
print(f"Registered contract at: {registered_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resolved Contract

# COMMAND ----------

print(f"Dataset:           {contract.dataset_name} v{contract.dataset_version}")
print(f"Source:            {contract.source_catalog}.{contract.source_schema}.{contract.source_table}")
print(f"Target:            {contract.target_catalog}.{contract.target_schema}.{contract.target_table}")
print(f"Coherence engine:  {contract.coherence.engine}")
print(f"  Bronze min:      {contract.coherence.bronze_min}")
print(f"  Silver min:      {contract.coherence.silver_min}")
print(f"  Gold min:        {contract.coherence.gold_min}")
print(f"Schema enforce:    {contract.schema_contract.enforce}")
print(f"Schema evolution:  {contract.schema_contract.evolution}")
print(f"Resolution:        {'enabled' if contract.resolution_enabled else 'disabled'}")
print(f"Temporal:          {'enabled' if contract.temporal_enabled else 'disabled'}")
print(f"Registry dir:      {registry_dir}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Raw Contract YAML

# COMMAND ----------

print(json.dumps(contract.raw, indent=2, default=str))
