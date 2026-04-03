# ÆtheriaForge

# Intelligent Data Transformation. Coherence-Scored. Evidence-Backed.

**EthereaLogic Databricks Suite — ÆtheriaForge**

Built by Anthony Johnson | EthereaLogic LLC

---

Every Medallion transformation introduces information loss. Most pipelines
ignore it. ÆtheriaForge measures it — scoring every transformation for
coherence, reconciling entities across source systems, merging temporal
conflicts, and enforcing schema contracts with versioned evolution. Every
operation produces append-only evidence. Nothing is assumed to have passed
unless the artifact says so.

## Executive Summary

| Leadership question | Answer |
| ------------------- | ------ |
| What business risk does this address? | Enterprises transforming data through Bronze → Silver → Gold layers have no mathematical model governing how much information loss is acceptable at each stage, no governed entity resolution across source systems, and no auditable evidence trail for transformation decisions. |
| What does this application prove? | A Databricks-deployable transformation engine that scores every operation for coherence, resolves entities across multiple sources, reconciles temporal conflicts, and surfaces queryable evidence artifacts in a read-only operator dashboard. |
| Why does it matter? | Moving data between layers is not the hard problem. Proving that the transformation preserved what it should, resolved what it needed to, and caught what it missed — with evidence — is the problem this solves. |

## The Business Problem

Enterprises operating mature Lakehouse architectures face three transformation
gaps that existing tools do not address:

- **Coherence loss is unmeasured.** Every transformation from Bronze to Silver
  to Gold discards, reshapes, or aggregates data. Without a coherence score,
  there is no way to know whether the output meets the target layer's quality
  threshold before writing it.

- **Entity resolution is ad-hoc.** Multiple source systems use different
  identifiers for the same entities. Lookup tables and manual mappings do not
  scale, version, or produce evidence of match decisions.

- **Temporal reconciliation is invisible.** CDC streams, SCD Type 2 dimensions,
  and batch loads create overlapping records with conflicting timestamps. Merge
  decisions happen silently with no audit trail.

## What This Repository Contains

| Surface | Purpose |
| ------- | ------- |
| `src/aetheriaforge/forge/` | Coherence-scored transformation engine (Shannon entropy v1.x) |
| `src/aetheriaforge/resolution/` | Cross-source entity resolution with configurable matching rules |
| `src/aetheriaforge/temporal/` | Temporal reconciliation across CDC, SCD Type 2, and batch sources |
| `src/aetheriaforge/schema/` | Schema enforcement and versioned evolution management |
| `src/aetheriaforge/evidence/` | Append-only transformation artifact writing shared across all modules |
| `src/aetheriaforge/orchestration/` | Workflow sequencing — runs all forge operations in order |
| `src/aetheriaforge/config/` | Forge contract and policy configuration |
| `app/` | Databricks App (Gradio) — read-only operator dashboard |
| `notebooks/` | Onboarding, execution, and evidence-review notebooks for Databricks |
| `resources/` | Databricks Asset Bundle pipeline, job, and app resource definitions |
| `templates/` | Forge contract, resolution policy, and schema contract templates |
| `specs/` | Canonical SDLC documents governing the product |
| `tests/` | Product test suite |

Every directory above contains a `README.md` describing its contents.

## How It Works

1. **Register datasets and forge contracts.** Each dataset is registered with a
   YAML contract specifying source location, target schema, resolution rules,
   temporal merge policy, and coherence thresholds.

2. **Run the forge pipeline.** The orchestration layer runs schema enforcement,
   coherence-scored transformation, entity resolution, and temporal
   reconciliation in sequence. Each module writes an append-only evidence
   artifact.

3. **Inspect transformation evidence.** The operator dashboard surfaces all
   artifacts with coherence scores, resolution outcomes, and merge decisions.

4. **Integrate with DriftSentinel (optional).** When bundled, ÆtheriaForge
   emits transformation events that DriftSentinel can consume for smarter
   publication gating, and receives drift payloads for auto-remediation.

## Decision / KPI Contract

**Business decision:** is the forged output trustworthy enough for the target
Medallion layer?

| KPI | Meaning |
| --- | ------- |
| `coherence_score` | Information preservation ratio for the transformation (0.0–1.0) |
| `resolution_confidence` | Match confidence for entity resolution decisions |
| `temporal_conflicts` | Count of temporal merge conflicts detected |
| `schema_conformance` | Percentage of records conforming to the target schema contract |
| `transformation_verdict` | PASS / WARN / FAIL for each forge operation |

**Control rule:** no transformation is assumed to have passed unless a PASS
artifact exists in the evidence directory. FAIL artifacts carry measured values
and thresholds.

## Databricks Fit

- **Databricks Asset Bundles** for source-controlled deployment
- **Databricks Apps (Gradio)** for a governed, read-only operator dashboard
- **Unity Catalog** for governed table publication and evidence volume
- **Databricks Lakeflow / Jobs** for scheduled forge pipeline execution
- ÆtheriaForge is dataset-agnostic — forge contracts handle per-dataset
  configuration regardless of schema shape or source system

## Product Suite Context

This is the second product in the **EthereaLogic Databricks Suite**.

| Product | Core Job | Primary Layer |
| ------- | -------- | ------------- |
| [DriftSentinel](https://github.com/Org-EthereaLogic/DriftSentinel) | Detect drift, block bad publishes | Bronze (detection) + Silver/Gold (gating) |
| **ÆtheriaForge** | Transform, reconcile, forge clean data | Silver (transformation engine) |
| EthereaLogic Suite (bundled) | Full governed Medallion pipeline | Bronze → Silver → Gold |

## Quickstart

```bash
git clone https://github.com/Org-EthereaLogic/AetheriaForge.git
cd AetheriaForge

make sync   # installs runtime + dev dependencies via uv
make test   # runs the test suite
```

### Databricks Bundle and App Deployment

```bash
make bundle-catalog-check CATALOG=my_catalog PROFILE=<profile>
make bundle-validate CATALOG=my_catalog PROFILE=<profile>
make app-deploy CATALOG=my_catalog PROFILE=<profile>
```

## Scope Boundary

ÆtheriaForge validates the coherence-scored transformation model using
registered datasets in a local and Databricks environment. It does not
constitute production-scale proof across arbitrary schema shapes or
multi-workspace deployments. The forge contract, evidence model, and
orchestration pattern are dataset-agnostic; the Databricks deployment path
requires a workspace with Unity Catalog enabled.

## Additional Documentation

- [Architecture and design rationale](specs/AF-SDD-001_Architecture_Blueprint.md)
- [Implementation plan](specs/AF-IP-001_Implementation_Plan.md)

---

MIT License. See [LICENSE](LICENSE) for details.
