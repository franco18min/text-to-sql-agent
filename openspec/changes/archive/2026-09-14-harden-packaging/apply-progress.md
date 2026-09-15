# Apply Progress: harden-packaging

**Mode**: Strict TDD  
**Workload**: single local apply (Decision needed: No)  
**Git**: no commit / no push

## Completed Tasks

- [x] 1.1 `tests/test_config.py` default Gemini without `.env`
- [x] 1.2 env override still allowed
- [x] 1.3 `GET /` and `/health` version `1.0.0`
- [x] 2.1 `__version__` + pyproject `1.0.0`
- [x] 2.2 FastAPI / root / health use `__version__`
- [x] 2.3 Field default `gemini-flash-lite-latest`
- [x] 3.1 Dockerfile `COPY env.example .env`
- [x] 3.2 `env.example` header `cp env.example .env`
- [x] 3.3 `.gitignore` exception `!data/eval/eval_set.json`
- [x] 3.4 eval set present on disk; `git add -f` / `git check-ignore` blocked (no `.git`)
- [x] 4.1 CI `pip install -e ".[dev]"`
- [x] 4.2 drop `--timeout=15`
- [x] 4.3 Makefile `docker-build`
- [x] 4.4 README Windows pytest + honest docker build (no recruiter rewrite)
- [x] 5.1 `pytest tests/ -v` → 154 passed; ruff not installed

### TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_config.py` | Unit | N/A (new) | ✅ Written (default was `gemini-2.0-flash-exp`) | ✅ Passed | ✅ 2 cases (unset vs override) | ➖ None needed |
| 1.2 | `tests/test_config.py` | Unit | N/A (new) | ➖ Override already passed (existing Field/env) | ✅ Passed | ✅ pairs with 1.1 | ➖ None needed |
| 1.3 | `tests/test_api.py` | Integration | ✅ 23/23 API | ✅ Written (`0.7.0` vs `1.0.0`) | ✅ Passed | ✅ `/` and `/health` | ➖ None needed |
| 2.1 | `tests/test_api.py` + `tests/test_packaging.py` | Unit | N/A | ✅ `__version__` 0.2.0 / pyproject 0.9.0 | ✅ Passed | ✅ two surfaces | ➖ None needed |
| 2.2 | `tests/test_api.py` | Integration | ✅ 23/23 | ✅ same RED as 1.3 | ✅ Passed | ✅ OpenAPI version via FastAPI + JSON | ➖ import `__version__` |
| 2.3 | `tests/test_config.py` | Unit | N/A | ✅ same RED as 1.1 | ✅ Passed | ✅ 1.1+1.2 | ➖ None needed |
| 3.1 | `tests/test_packaging.py` | Unit | N/A (new) | ✅ `COPY .env.example` | ✅ Passed | ➖ Structural | ➖ None needed |
| 3.2 | `tests/test_packaging.py` | Unit | N/A | ✅ `cp .env.example` | ✅ Passed | ➖ Structural | ➖ None needed |
| 3.3 | `tests/test_packaging.py` | Unit | N/A | ✅ missing negation | ✅ Passed | ➖ Structural | ➖ None needed |
| 3.4 | `tests/test_packaging.py` | Unit | N/A | file exists on disk | ➖ `git` unavailable | ➖ Single | ➖ N/A |
| 4.1 | `tests/test_packaging.py` | Unit | N/A | ✅ piecemeal pip | ✅ Passed | ➖ Structural | ➖ None needed |
| 4.2 | `tests/test_packaging.py` | Unit | N/A | ✅ `--timeout=15` present | ✅ Passed | ➖ Structural | ➖ None needed |
| 4.3 | `tests/test_packaging.py` | Unit | N/A | ✅ no target | ✅ Passed | ➖ Structural | ➖ None needed |
| 4.4 | `tests/test_packaging.py` | Unit | N/A | ✅ missing pytest/docker lines | ✅ Passed | ✅ pytest + run_tests + docker build + `[dev]` | ➖ None needed |
| 5.1 | `tests/` | Unit+API | ✅ 154/154 | N/A verify | ✅ 154 passed | N/A | ruff missing |

### Test Summary
- **Total tests written**: 11 new (2 config + 8 packaging + 1 `__version__`; plus 2 assertions on existing API tests)
- **Total tests passing**: 154
- **Layers used**: Unit (config + packaging files), Integration (TestClient)
- **Approval tests**: None — no behavior-preserving refactor of existing logic
- **Pure functions created**: 0 (`__version__` constant + Field default)

## Deviations
- Task 3.4: workspace is not a git repository (`fatal: not a git repository`). Could not run `git add -f` or `git check-ignore`. `.gitignore` no longer ignores `data/eval/eval_set.json`; `eval_results.json` still matches `data/eval/*.json`. File `data/eval/eval_set.json` is present on disk.
- Task 5.1: `ruff` not installed (`No module named ruff`); skipped as optional.

## Remaining Tasks
None.

## Workload / PR Boundary
- Mode: single local apply
- Current work unit: Unit 1 (clone/test/Docker + version/model)
- Boundary: full change `harden-packaging`
- Estimated review budget impact: Low (tasks forecast 80–180 lines)
