# Constitution for ÆtheriaForge

This constitution defines the governing principles for ÆtheriaForge development.

## Scope

It applies to:

- product code for coherence-scored transformation, entity resolution, temporal
  reconciliation, and schema enforcement,
- Databricks bundle, notebook, and deployment surfaces,
- workflow orchestration and operator surfaces,
- DriftSentinel integration interface (when bundled),
- documentation, reporting, and governance artifacts.

## Required Decision Order

When principles conflict, resolve them in this order:

1. Safety and correctness.
2. Evidence traceability.
3. Security and secret hygiene.
4. Simplicity and proportionality.
5. Reproducibility and operational reliability.
6. Performance and speed.

## Governing Principles

### P1. Safety, Correctness, and Repository Integrity

- Never ship a change that knowingly violates acceptance criteria, policy
  boundaries, or operator safety.
- Prefer explicit failure over silent unsafe behavior.
- Treat protected branches, frozen contracts, and publication gates as hard
  boundaries.

### P2. Evidence Traceability

- Every transformation, resolution, and coherence claim must map to concrete
  evidence.
- Reports must distinguish measured facts from interpretation.
- Missing evidence blocks completion claims.

### P3. Security and Secret Hygiene

- No credentials, tokens, or secret material in repository content or committed
  artifacts.
- Use least-privilege credentials and rotate exposed keys immediately.
- Treat policy violations and secret exposure as hard failures.

### P4. Simplicity and Proportionality

- Match implementation complexity to the size and risk of the problem.
- Avoid speculative abstractions and UI-first scaffolding until the backend
  contract is proven.
- Prefer direct implementations until there is measured evidence for a broader
  pattern.

### P5. Reproducibility and Operational Reliability

- Capture inputs, outputs, timestamps, and commit metadata where the runtime
  supports it.
- Keep artifacts append-only and audit-friendly.
- Build workflows so another operator can replay the result or explain why it
  cannot be replayed.

### P6. Human Control and Transparency

- Provide explicit operator controls such as cancel, retry, resume, and review.
- Record overrides with actor, reason, and resulting effect.
- Do not hide recovery behavior behind opaque automation.

### P7. Validation Before Commercialization

- Internal validation gates must be met before commercialization claims.
- MVP or packaging readiness depends on verified evidence and governance
  review, not anecdotal success.

### P8. Entropy Engine Integrity

- v1.x uses Shannon entropy exclusively. No proprietary UMIF material.
- The v3.0 migration path is a strategic asset. The performance comparison
  methodology must be rigorous and evidence-backed.
- Entropy engine changes require a version bump and traceability update.

## Evidence Integrity Rules

- PASS claims require machine-verifiable evidence and human-readable evidence.
- DriftSentinel may inform design, but only this repository's canonical
  `specs/` documents govern the ÆtheriaForge product.
- Sibling project code informs extraction, but it does not define the
  ÆtheriaForge product contract.

## Prohibited Anti-Patterns

- Placeholder-driven delivery in production files.
- Fabricated metrics or unverifiable KPI claims.
- Pattern inflation from speculative future requirements.
- Runtime dependency on DriftSentinel or sibling project clones.
- Destructive artifact mutation used to hide failures.
- Declaring PASS from low-integrity evidence.
- Including proprietary UMIF constructs in v1.x codebase.

## Relationship to Other Governance Docs

- `AGENTS.md` defines operational behavior for coding agents.
- `DIRECTIVES.md` defines enforceable repository rules.
- `specs/*.md` defines the ÆtheriaForge contract and product behavior.
