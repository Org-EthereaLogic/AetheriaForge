# Dependabot Alert Remediation Record — 2026-06-27T01:20:48Z

## Scope

Resolve all 14 open GitHub Dependabot vulnerability alerts
(`Org-EthereaLogic/AetheriaForge`, alerts #5–#18) detected in `uv.lock`.
All 14 alerts collapse to **5 transitive dependencies** (pulled in primarily
via `gradio` in the `app` dependency group, plus `databricks-sdk`/`requests`).
Remediation is a targeted lockfile version bump — no first-party source or
`pyproject.toml` constraint change was required, because the resolver reaches
patched versions without any upstream cap blocking the upgrade.

## Alert → Package → Fix Mapping

| Alert | Severity | Package | Vulnerable range | First patched | Resolved-to |
| --- | --- | --- | --- | --- | --- |
| #6 | High | urllib3 | `>= 2.6.0, < 2.7.0` | 2.7.0 | **2.7.0** |
| #7 | High | urllib3 | `>= 1.23, < 2.7.0` | 2.7.0 | **2.7.0** |
| #5 | High | python-multipart | `< 0.0.27` | 0.0.27 | **0.0.32** |
| #13 | High | python-multipart | `< 0.0.30` | 0.0.30 | **0.0.32** |
| #11 | Low | python-multipart | `< 0.0.30` | 0.0.30 | **0.0.32** |
| #10 | Low | python-multipart | `< 0.0.30` | 0.0.30 | **0.0.32** |
| #12 | Low | python-multipart | `< 0.0.31` | 0.0.31 | **0.0.32** |
| #18 | High | starlette | `>= 0.4.1, < 1.3.1` | 1.3.1 | **1.3.1** |
| #16 | High | starlette | `< 1.1.0` | 1.1.0 | **1.3.1** |
| #15 | Moderate | starlette | `< 1.1.0` | 1.1.0 | **1.3.1** |
| #9 | Moderate | starlette | `<= 1.0.0` | 1.0.1 | **1.3.1** |
| #17 | Low | starlette | `< 1.3.0` | 1.3.0 | **1.3.1** |
| #14 | High | cryptography | `>= 0.5.0, < 48.0.1` | 48.0.1 | **49.0.0** |
| #8 | Moderate | idna | `< 3.15` | 3.15 | **3.18** |

Every resolved-to version meets or exceeds the GitHub-advisory
`first_patched_version`, so all 14 alerts are cleared.

## Change Applied

Single command, scoped to the five affected packages:

```bash
uv lock \
  --upgrade-package cryptography \
  --upgrade-package idna \
  --upgrade-package python-multipart \
  --upgrade-package starlette \
  --upgrade-package urllib3
```

Version transitions. **Scope note:** this claim and the `git diff --stat`
below describe the *security-remediation commit alone* — within that commit only
these five package entries (version + hash blocks) change in `uv.lock`; no
packages are added or removed. The pull request that carries this commit also
includes two prior-session `chore` commits; one of them (`add pre-commit hooks`)
separately adds `pre-commit` to `pyproject.toml` and locks its dependencies
(`cfgv`, `identify`, `nodeenv`, `virtualenv`, …). Those additions belong to the
hook commit, not to this security remediation, so they are intentionally outside
the scope recorded here.

Version transitions (security commit only):

| Package | Before | After |
| --- | --- | --- |
| cryptography | 46.0.7 | 49.0.0 |
| idna | 3.11 | 3.18 |
| python-multipart | 0.0.26 | 0.0.32 |
| starlette | 1.0.0 | 1.3.1 |
| urllib3 | 2.6.3 | 2.7.0 |

`git diff --stat`: `uv.lock | 123 +++--- , 1 file changed, 60 insertions(+), 63 deletions(-)`.

## Verification Evidence (replayable)

| Check | Command | Result |
| --- | --- | --- |
| Lockfile consistency | `uv lock --check` | Resolved 100 packages, no drift |
| One entry per package | `grep -c '^name = "<pkg>"$' uv.lock` | exactly 1 each — no stale vulnerable duplicate |
| Env install | `make sync` | upgraded versions installed |
| Lint | `make lint` | All checks passed |
| Typecheck | `make typecheck` | Success: no issues in 53 source files |
| Test suite | `make test` | **304 passed** in ~30s |
| Gradio app builds | `app.build_app()` + `gradio.routes.App.create_app(demo)` | Blocks built, FastAPI/starlette routing app created OK |
| cryptography OpenSSL | `backend.openssl_version_text()` | `OpenSSL 4.0.1 9 Jun 2026` (patched build, clears #14) |
| Runtime urllib3 path | `import requests, urllib3` | requests 2.33.1 uses urllib3 2.7.0 |

Installed runtime versions confirmed via `importlib.metadata`:
cryptography 49.0.0 · idna 3.18 · python-multipart 0.0.32 · starlette 1.3.1 ·
urllib3 2.7.0.

## Risk Notes

- `starlette 1.0.0 → 1.3.1` and `python-multipart 0.0.26 → 0.0.32` are the
  largest behavioral jumps. Both are exercised by the `app` group through
  `gradio`. The 43-test `tests/test_app.py` suite passed, and the full Gradio
  Blocks → FastAPI app construction path was instantiated successfully, so the
  operator dashboard server stack is compatible with the bumped versions.
- No first-party source change was needed; the bump is confined to `uv.lock`.

## Alert Closure

The five bumps land on branch `claude/admiring-brahmagupta-3e8f8e`. The 14
alerts auto-close once the patched `uv.lock` reaches the default branch (`main`)
and Dependabot re-scans — they are *fixed*, not dismissed. No manual dismissal
was performed (dismissal would mislabel a real fix).
