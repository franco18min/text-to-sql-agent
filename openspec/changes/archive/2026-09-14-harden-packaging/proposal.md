# Proposal: Harden Packaging

## Intent

Clone → test → Docker must match the repo: CI installs the same extras as README, Docker copies `env.example`, `eval_set.json` ships, Gemini default is `gemini-flash-lite-latest`, version is `1.0.0` everywhere, and Windows pytest is documented.

## Scope

### In Scope

- CI: `pip install -e ".[dev]"` (langgraph available to `tests/test_agent.py`)
- Dockerfile: `COPY env.example .env`; `env.example` header `cp` path
- `.gitignore`: ship `data/eval/eval_set.json`; ignore generated eval JSON
- Default `gemini_model`: `gemini-flash-lite-latest`
- Version `1.0.0`: `pyproject.toml`, `app/__init__.py`, FastAPI app, `GET /`, health
- README: Windows `python -m pytest tests/ -v` and `run_tests.py`; honest `docker build` (add `docker-build` Makefile target or drop the fake one)

### Out of Scope

- Retry, schema HTTP, eval narrative/screenshots, auth, streaming
- Split `test` vs `dev` extras, Makefile Windows rewrite, Databricks extras split

## Capabilities

### New Capabilities

- `ci-editable-install`: CI uses editable `[dev]` install matching clone docs
- `docker-env-example`: Image build copies tracked `env.example`
- `eval-set-shipping`: Tracked `eval_set.json`; generated eval JSON stay ignored
- `gemini-default-model`: Config default matches `env.example` flash-lite-latest
- `unified-version`: Single `1.0.0` across package, app, health, `/`
- `windows-pytest-docs`: README documents pytest / `run_tests.py` and real docker build

### Modified Capabilities

None (do not change agent/schema main specs)

## Approach

Approach 1 (surgical). Align files; no packaging rewrite. Track `eval_set.json` only; ignore results (GT optional/ignored). Document `run_tests.py`; drop `--timeout=15` or add `pytest-timeout` so the wrapper does not lie. Keep Unix Makefile except optional `docker-build`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `.github/workflows/ci.yml` | Modified | `pip install -e ".[dev]"` |
| `Dockerfile` | Modified | `COPY env.example .env` |
| `env.example` | Modified | Header `cp` path |
| `.gitignore` | Modified | Exception for `eval_set.json` |
| `data/eval/eval_set.json` | Modified | Tracked fixture |
| `app/config.py` | Modified | Gemini default |
| `pyproject.toml`, `app/__init__.py`, `app/main.py`, `app/api/health.py` | Modified | `1.0.0` |
| `README.md`, `Makefile`, `run_tests.py` | Modified | Docs + timeout honesty |
| `tests/test_api.py` | Modified | TDD: health version/model if asserted |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CI slower / pin fail (langgraph 0.2 / Py 3.11) | Med | `[dev]` extras; fix pins if install fails |
| Accidental eval results commit | Low | Ignore `eval_results.json`; `git add -f` set only |
| `run_tests.py --timeout` without pytest-timeout | Med | Remove flag or add extra |
| Docker build ≠ runnable demo | Low | Example `.env` unblocks build only |

## Rollback Plan

Revert the change branch. Restore piecemeal CI, `.env.example` COPY, old gitignore, old Gemini/version strings, README `make` commands.

## Dependencies

- Tracked `eval_set.json` (force-add if still ignored)
- Existing `[project.optional-dependencies] dev` in `pyproject.toml`

## Success Criteria

- [ ] Fresh clone: `pip install -e ".[dev]"` then pytest collects including agent tests
- [ ] `docker build` succeeds past env COPY
- [ ] Clone includes `data/eval/eval_set.json`
- [ ] Unset `GEMINI_MODEL` → `gemini-flash-lite-latest`
- [ ] All version surfaces `1.0.0`
- [ ] README Windows pytest + real docker command
