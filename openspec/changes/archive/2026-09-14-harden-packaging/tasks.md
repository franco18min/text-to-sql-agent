# Tasks: Harden Packaging

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 80–180 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Align clone/test/Docker + version/model | PR 1 | Tests + packaging + README/CI; under budget |

## Phase 1: RED — failing tests

- [x] 1.1 Add `tests/test_config.py`: monkeypatch-delete `GEMINI_MODEL`, no `.env`; assert `gemini-flash-lite-latest` (gemini-default-model: Unset GEMINI_MODEL without .env). Run `pytest tests/test_config.py -v` — fail.
- [x] 1.2 Same file: set `GEMINI_MODEL` override; assert that value (Env override still allowed). Fail until Field default exists.
- [x] 1.3 In `tests/test_api.py`: TestClient `GET /` and health include `"version": "1.0.0"` (unified-version: Root and health report 1.0.0). Fail vs 0.9.0/0.7.0.

## Phase 2: GREEN — version and config

- [x] 2.1 Set `app/__init__.py` `__version__ = "1.0.0"`; `pyproject.toml` `version = "1.0.0"` (Package matches API).
- [x] 2.2 `app/main.py` FastAPI `version=` and `GET /` use `__version__`; `app/api/health.py` health `version=__version__`. Pass 1.3.
- [x] 2.3 `app/config.py` Field default `gemini-flash-lite-latest`. Pass 1.1–1.2.

## Phase 3: GREEN — packaging files

- [x] 3.1 `Dockerfile`: `COPY env.example .env` (Build copies env.example).
- [x] 3.2 `env.example` header `cp env.example .env` (Template header names the file).
- [x] 3.3 `.gitignore`: keep `data/eval/*.json`; add `!data/eval/eval_set.json` (Clone includes eval set; Results stay untracked).
- [x] 3.4 Track `data/eval/eval_set.json` (`git add -f` if ignored). Confirm `eval_results.json` ignored via `git check-ignore`.

## Phase 4: GREEN — CI, wrapper, docs

- [x] 4.1 `.github/workflows/ci.yml`: `pip install -e ".[dev]"`; keep dummy env, pytest/cov (Agent tests import langgraph; Clone docs match CI).
- [x] 4.2 `run_tests.py`: drop `--timeout=15`.
- [x] 4.3 `Makefile`: add `docker-build` → `docker build -t text-to-sql-agent .`.
- [x] 4.4 `README.md`: `python -m pytest tests/ -v` + `run_tests.py` without Make; `docker build -t text-to-sql-agent .` (Windows pytest without Make; Docker build docs are honest). Keep README `[dev]` install aligned with CI.

## Phase 5: REFACTOR / verify

- [x] 5.1 `pytest tests/ -v`; `ruff check app/ tests/ scripts/ ui/` if available. No extra extras or Makefile Windows rewrite.
