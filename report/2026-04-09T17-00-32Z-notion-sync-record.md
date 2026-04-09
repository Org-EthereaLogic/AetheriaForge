# Notion Sync Record

| Field | Value |
| --- | --- |
| Timestamp | 2026-04-09T17:00:32Z |
| Target Page | AetheriaForge UMIF Data Quality Drift Foundry |
| Page ID | 33af5d74-5418-42d8-bf9d-a6bdeeb88956 |
| Sync Mode | direct-update |
| Operator | Claude Code (v0.1.4 PyPI release addendum) |

## Scope

Second Notion update of the 2026-04-09 sync cycle. The earlier sync
(`report/2026-04-09T16-46-56Z-notion-sync-record.md`) reported that the
0.1.4 version bump had landed on `main` but explicitly flagged that no
PyPI release had been triggered and a separate operator action was
required. This addendum records the actual PyPI publish of 0.1.4, the
partial-success of the publish workflow run, and the follow-up linker
fix, and updates the public page to reflect the real PyPI state.

## Pre-Flight Page Read

- Page fetched at `2026-04-09T16:46:38.802Z` snapshot (post-prior-sync
  state) — `public-page-observed`
- Target identity re-confirmed: `⚒️ AetheriaForge — Data Quality + Drift
  Foundry`, page id `33af5d74-5418-42d8-bf9d-a6bdeeb88956` —
  `public-page-observed`
- Prior recorded commit on the page: `5d554a6` — `public-page-observed`
- Post-update re-fetch at `2026-04-09T17:00:19.062Z` confirms both edits
  landed on the live page — `public-page-observed`

## Changes Applied (direct-update)

### Implementation Status table
- **Commit** cell — `5d554a6` → `b55ea85`. `repo-verified` against
  `git rev-parse HEAD` after the `fix(ci)` commit `a8e1119` and the
  release evidence commit `b55ea85` landed on `main`.

### Completed Phases list
- Item **25** rewritten in place (no new item inserted) to:
  - Rename it from "v0.1.4 Release & Bundle Validate Auth Unblock" to
    "v0.1.4 Release, PyPI Publish & Bundle Validate Auth Unblock".
  - Add the statement "**v0.1.4 is now live on PyPI**" with a link to
    the project URL, upload timestamp (`2026-04-09T16:56:46Z`), and
    wheel/sdist sizes (`59338 bytes` / `35650895 bytes`).
    `public-page-observed` for the PyPI upload (replayed via
    `GET https://pypi.org/pypi/etherealogic-aetheriaforge/0.1.4/json`).
  - Add a link to GitHub release `v0.1.4`
    (`Org-EthereaLogic/AetheriaForge` releases).
  - Document the publish workflow run id (`24202632527`), the PyPI step
    PASS, the post-upload linker step FAIL, the HTTP 422 root cause
    (`github_repository` being sent as `owner/repo` instead of a bare
    name matching `^[A-Za-z0-9.\-_]+$`), and the fix commit
    (`a8e1119`) with the regression assertion in
    `tests/test_packaging_metadata.py`. `repo-verified` against
    the diff of `.github/workflows/publish.yml` and the workflow run
    log.
  - Note that the linker fix applies to future releases only because
    PyPI rejects re-uploads of the same version.
  - Point to `report/2026-04-09T16-58-31Z-v0.1.4-pypi-release.md` for
    full replayable evidence.

No other Implementation Status, Validation, Next, or Risks-and-Blockers
edits were needed in this update.

## Validation State at Addendum Time

| Check | Result | Classification |
| --- | --- | --- |
| Lint (`make lint` → `ruff check .`) | PASS | repo-verified |
| Type-check (`make typecheck` → `mypy src/aetheriaforge tests`) | PASS — 52 source files | repo-verified |
| Tests (`make test` → `pytest`) | PASS — 300 tests in 19 files | repo-verified |
| Packaging regression (`uv run pytest tests/test_packaging_metadata.py -q`) | PASS — 2 tests | repo-verified |
| PyPI artifact check (`curl /pypi/etherealogic-aetheriaforge/0.1.4/json`) | PASS — both `.whl` and `.tar.gz` listed at upload time `2026-04-09T16:56:46Z` | public-page-observed |
| GitHub release (`gh release view v0.1.4`) | present at `https://github.com/Org-EthereaLogic/AetheriaForge/releases/tag/v0.1.4` | public-page-observed |
| Publish workflow run `24202632527` | `failure` final status; PyPI publish step PASS, post-upload linker step FAIL | public-page-observed |

## Git State

| Field | Value |
| --- | --- |
| Branch | main |
| HEAD commit | b55ea85 |
| Prior main tip at the start of the addendum | 9efbf9f |
| Push | success to `origin/main` (`9efbf9f..b55ea85  main -> main`) |
| Tag pushed this cycle | `v0.1.4` → `9efbf9fdf234d1c52b896eaed16f412808793834` |

### Commits added this sync addendum

1. `a8e1119` — `fix(ci): strip owner from github_repository in publish
   linker`
   - `.github/workflows/publish.yml`: payload field changed from
     `os.environ["GITHUB_REPOSITORY"]` to
     `os.environ["GITHUB_REPOSITORY"].split("/", 1)[-1]` so the GitHub
     artifact-metadata storage-record endpoint receives a bare
     repository name and no longer rejects the request with HTTP 422.
   - `tests/test_packaging_metadata.py`: new assertion that the shipped
     workflow contains the exact `.split("/", 1)[-1]` expression, so
     the bug cannot silently return.

2. `b55ea85` — `chore(report): record v0.1.4 PyPI release evidence`
   - `report/2026-04-09T16-58-31Z-v0.1.4-pypi-release.md`: append-only
     record documenting the actual outcome of the v0.1.4 release cycle,
     the partial-success classification of publish workflow run
     `24202632527`, and the explanation for not cutting a v0.1.5 patch
     release solely to re-trigger the workflow.

## PyPI Publish — repo-verified + public-page-observed

| Field | Value |
| --- | --- |
| Package | etherealogic-aetheriaforge |
| Version | 0.1.4 |
| Trigger | GitHub release `v0.1.4` |
| Workflow run | `24202632527` |
| PyPI upload step | PASS |
| Post-upload linker step | FAIL (HTTP 422 on `github_repository` pattern) |
| Wheel | `etherealogic_aetheriaforge-0.1.4-py3-none-any.whl` (59338 bytes) |
| Sdist | `etherealogic_aetheriaforge-0.1.4.tar.gz` (35650895 bytes) |
| Upload time | `2026-04-09T16:56:46Z` |
| Installable today | `pip install etherealogic-aetheriaforge==0.1.4` |

## Notion Page State

- Page read before update — target identity confirmed and prior
  `5d554a6` commit hash observed (`public-page-observed`)
- Page updated via Notion MCP (`update_content`) — two content edits
  submitted in one call; return payload
  `{"page_id": "33af5d74-5418-42d8-bf9d-a6bdeeb88956"}` and a follow-up
  `notion-fetch` at `2026-04-09T17:00:19.062Z` confirmed both edits are
  visible on the live page (`public-page-observed`)
- No tasks created or updated on Notion in this addendum
- No property edits; only body content edits

## Claim Classification Summary

- `repo-verified`: validation results (ruff, mypy, pytest), commit
  hashes, tag target, content of the fix in `publish.yml`, content of
  the new regression assertion.
- `public-page-observed`: PyPI upload facts (filenames, sizes, upload
  time) come from
  `https://pypi.org/pypi/etherealogic-aetheriaforge/0.1.4/json`; the
  GitHub release, tag, and workflow run details come from
  `gh release view`, `gh run list`, and `gh run view --log-failed`;
  Notion pre- and post-update snapshots come from the `notion-fetch`
  tool.
- `operator-reported`: none in this addendum.
