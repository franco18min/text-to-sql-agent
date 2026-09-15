## Exploration: Clone → test → docker must not lie

### Current State

Clone/test/docker docs and artifacts disagree with files on disk. All six orchestrator claims are confirmed from source:

1. **CI piecemeal deps.** `.github/workflows/ci.yml` installs pytest + FastAPI/pydantic/sqlparse only. It does **not** `pip install -e ".[dev]"`. `tests/test_agent.py` imports `app.agent.graph` (`from langgraph.graph import END, StateGraph`). CI would fail once those tests collect. README tells clones to use `pip install -e ".[dev]"`, which *does* pull langgraph from `pyproject.toml`. Two install paths, two realities.

2. **Dockerfile copies a missing file.** `COPY .env.example .env` but the repo file is `env.example` (README `cp env.example .env` is correct; `env.example` header still says `cp .env.example .env`). Image build fails at that layer.

3. **Eval JSON gitignored.** `.gitignore` has `data/eval/*.json` and `*.csv`. `eval_set.json` (30 questions) plus `eval_gt.json` / `eval_results.json` exist locally but a fresh clone following gitignore would not receive the eval set. `data/eval/README.md` treats `eval_set.json` as the shipped fixture.

4. **Gemini default vs docs.** `app/config.py` `gemini_model` default is `gemini-2.0-flash-exp`. `env.example`, tests (env override), `docs/architecture.md`, and `docs/eval-results.md` use `gemini-flash-lite-latest`. Health tests only pass because they monkeypatch `GEMINI_MODEL`. Docker with no env would bake the blocked experimental id.

5. **Version drift.** `pyproject.toml` `0.9.0`; FastAPI `app.main` + `GET /` + `app/api/health.py` `0.7.0`; `app/__init__.py` `__version__` `0.2.0`. Target unify: **1.0.0**.

6. **Windows vs Makefile.** `Makefile` is Unix (`grep`/`awk`/`find`, `run-both` with `&`). README Quick start and Tests sections say `make test` / `make docker-build`. There is **no** `docker-build` target. `run_tests.py` exists (Windows-friendly pytest wrapper) but is undocumented in README Tests; it also passes `--timeout=15` which is not in `[project.optional-dependencies] dev`.

**Extra (same theme):** Dockerfile `COPY data/ ./data/` after gitignore means Docker context may lack eval JSON even if COPY path exists. `requirements.txt` includes pytest + Databricks extras; Dockerfile installs full `requirements.txt` (heavy but self-consistent if build gets past `.env.example`).

Out of scope: retry, schema HTTP, eval narrative/screenshots, auth, streaming.

### Affected Areas

- `.github/workflows/ci.yml` — install must match what pytest imports
- `pyproject.toml` — version 1.0.0; optional: keep `[dev]` as CI source of truth
- `Dockerfile` — `COPY env.example .env`; eval files in image only if tracked/not ignored
- `env.example` — header `cp` path; remains GEMINI source of truth
- `.gitignore` — stop ignoring shipped eval fixture(s)
- `app/config.py` — default `gemini_model`
- `app/__init__.py`, `app/main.py`, `app/api/health.py` — single version
- `README.md` — pytest on Windows; drop or add `make docker-build`; clone path
- `Makefile` — optional `docker-build`; leave Unix as-is except if adding that target
- `run_tests.py` — document; optionally drop `--timeout` or add pytest-timeout
- `data/eval/eval_set.json` — must be commitable (and README there)
- Tests: `tests/test_api.py` health version/model if defaults/version change; config default test if added under strict TDD

### Approaches

1. **Surgical truth-telling (recommended)** — Align CI, Docker COPY, gitignore exceptions, Gemini default, versions, and README pytest/docker commands. No packaging-system rewrite.
   - Pros: Small, matches “must not lie”; CI becomes the same install as README; Docker builds; eval set clones.
   - Cons: `pip install -e ".[dev]"` in CI is heavier than today’s slim list (langgraph/langchain/gemini/databricks pins). Mitigate with extras `dev` only plus a `test` extra if we want to skip Databricks in CI—but graph import still needs langgraph.
   - Effort: Low

2. **Split extras (`test` vs `dev` vs `runtime`)** — CI `pip install -e ".[test]"` with langgraph + pytest, omit Databricks/MLflow.
   - Pros: Faster CI than full runtime.
   - Cons: Extra maintenance vs `requirements.txt`/`pyproject` already duplicated; easy to drift again.
   - Effort: Medium

3. **Docs-only** — Document workarounds (`COPY env.example`, `python -m pytest`) without fixing CI/Docker/gitignore.
   - Pros: Tiny.
   - Cons: Clone → test → docker still lies; Docker still fails.
   - Effort: Low (rejected)

### Recommendation

Use **Approach 1**. Single install command in CI: `pip install -e ".[dev]"` (or equivalent that includes langgraph). Fix Dockerfile to `COPY env.example .env`. Change gitignore to ignore only generated eval artifacts (`eval_results.json`, maybe `eval_gt.json`) and **track `eval_set.json`**. Set `gemini_model` default to `gemini-flash-lite-latest`. Set `1.0.0` in pyproject, `__version__`, FastAPI app, health, and `/`. README: Windows `python -m pytest tests/ -v` (and mention `run_tests.py`); replace `make docker-build` with `docker build -t text-to-sql-agent .` or add that Makefile target. Do not rewrite Makefile for Windows.

Eval GT: prefer tracking `eval_set.json` only; keep results gitignored; GT optional (regenerable) — propose tracking set, ignore results, ignore or exception-document GT.

### Risks

- CI time/size jumps once real runtime deps install; pin failures on langgraph 0.2.0 / langchain 0.2.0 on Python 3.11.
- Force-adding previously ignored `data/eval/*.json` needs `git add -f`; results JSON may contain run-specific noise if accidentally committed.
- Health tests assert `version` only if we add that; current tests do not assert API version, so version unify can miss tests unless TDD adds one.
- `run_tests.py --timeout=15` still fails on clones without pytest-timeout if we document it as the Windows path without fixing the flag.
- Docker still needs a real `.env` at runtime for Databricks/Gemini; COPY example only unblocks **build**, not a working demo without `--env-file`.

### Ready for Proposal

Yes. Orchestrator should run **sdd-propose** for `harden-packaging`: CI editable install, Docker `env.example`, gitignore eval-set exception, Gemini default + version 1.0.0, README Windows pytest / honest docker build. Do not reopen retry, schema HTTP, eval writeup, auth, or streaming.
