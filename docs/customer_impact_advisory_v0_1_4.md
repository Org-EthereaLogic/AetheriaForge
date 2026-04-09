# Customer Impact Advisory for v0.1.4

## Summary

Version `0.1.4` closes the remaining release-path issue from `0.1.3` and
supersedes the coherence-scoring defect fixed in `0.1.3`.

- If you used `0.1.2` or earlier for schema-backed forge runs, you should rerun
  the affected forge workflows after upgrading because valid transformations may
  have been scored too low and marked `WARN` or `FAIL`.
- If you used `0.1.3`, no customer data rerun is required. The remaining issue
  in `0.1.3` was limited to GitHub release bookkeeping after a successful PyPI
  publish and did not affect installed package behavior.

## Affected Versions

- `0.1.2` and earlier:
  schema-backed coherence scoring could under-credit renamed, projected, or
  multi-source contract-backed outputs.
- `0.1.3`:
  package behavior was correct; only the repository publish workflow could end
  in a false failure after upload.

## Rerun Exactly These Workflows

Rerun after upgrading to `0.1.4` if you previously ran them on `0.1.2` or
earlier and relied on the resulting `coherence_score`, `PASS/WARN/FAIL`
verdict, evidence artifact, or dashboard status:

- any local Python workflow that calls `ForgePipeline.run(...)`
- any local Python workflow that calls `ForgeEngine.transform_and_forge(...)`
- any local or notebook workflow that transforms through a schema contract and
  records forge evidence
- any Databricks bundle job run such as
  `databricks bundle run forge_job -p <profile> --target dev --var="catalog=<existing_uc_catalog>"`
- any notebook or scheduled run whose operator decision depended on a forge
  artifact generated from a schema-backed transformation

## Workflows That Do Not Need Rerun

- ingest-only reads
- schema enforcement used outside final forge scoring
- entity resolution or temporal reconciliation runs used outside final forge
  scoring
- any workflow already rerun on `0.1.3`
- any installed use of `0.1.3` that did not depend on GitHub release automation

## Recommended Operator Action

1. Upgrade to `0.1.4`.
2. Rerun the affected forge workflows from their original source inputs.
3. Replace prior operational decisions with the new evidence artifacts where
   the earlier run came from `0.1.2` or earlier.
