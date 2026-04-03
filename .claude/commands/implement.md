# implement

Implement scoped ÆtheriaForge work under the canonical SDLC contract.

## Workflow

1. Read `CLAUDE.md` and the relevant `specs/AF-*.md` documents.
2. Preserve the file taxonomy defined in `specs/AF-SDD-001`.
3. Update traceability and documentation when the change affects requirements,
   design, testing, or build instructions.
4. Run the applicable validation commands from `CLAUDE.md`.

## Rules

- Do not treat narrative docs as canonical over `specs/`.
- Do not introduce hidden behavior, unverifiable claims, or placeholder text.
- Keep evidence and verification expectations explicit.
- No runtime dependency on DriftSentinel or sibling project clones.
- No proprietary UMIF material in v1.x codebase.
