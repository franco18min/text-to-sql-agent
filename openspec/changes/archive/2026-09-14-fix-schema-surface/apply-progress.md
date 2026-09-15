# Apply Progress: fix-schema-surface

**Change**: fix-schema-surface
**Mode**: Strict TDD
**Status**: 13/13 tasks complete. Ready for verify.

## Completed Tasks

- [x] 1.1 GET /schema catalog, bare table, full_name
- [x] 1.2 Spark → HTTP column mapping + empty comment
- [x] 1.3 listing failure → 200 tables=[]
- [x] 2.1 get_schema two-/three-arg core calls + HTTP mapper
- [x] 2.2 HTTP table shape; SchemaResponse list[dict] + comment
- [x] 2.3 Streamlit keys unchanged (no UI edit)
- [x] 2.4 Extract `_spark_column_to_http`
- [x] 3.1 CORS Origin tests (Cloud, HF, localhost, loopback, no globs)
- [x] 3.2 allow_origins + allow_origin_regex
- [x] 3.3 CORS block cleaned
- [x] 4.1 notebook list_tables two-arg
- [x] 4.2 notebook describe three-arg + Spark keys + empty-safe loop
- [x] 5.1 pytest tests/ -v → 143 passed

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_api.py` | Integration | ✅ 15/15 `test_api.py` | ✅ Written (TypeError on string table names) | ✅ Passed | ✅ 1.2 second table/column path | ➖ tests only |
| 1.2 | `tests/test_api.py` | Integration | ✅ same | ✅ Written (Spark keys leaked) | ✅ Passed | ✅ missing comment → `""` | ➖ tests only |
| 1.3 | `tests/test_api.py` | Integration | ✅ same | ✅ Written (already 200 empty — locked contract) | ✅ Passed | ✅ catalog/schema still set | ➖ tests only |
| 2.1–2.4 | `tests/test_api.py` | Integration | ✅ 15/15 | ✅ used 1.x tests | ✅ Passed | ✅ customer + two columns | ✅ `_spark_column_to_http` |
| 2.3 | n/a | Approval | N/A | ➖ no UI change | `ui/streamlit_app.py` still `t["table"]`, `col.get("name")`/`type` | ➖ Single | ➖ None needed |
| 3.1–3.3 | `tests/test_api.py` | Integration | ✅ 15/15 | ✅ Cloud/HF ACAO missing; globs present | ✅ Passed | ✅ 4 origins + glob-absence | ✅ regex + exact localhost |
| 4.1–4.2 | `tests/test_demo_notebook.py` | Unit | N/A (new) | ✅ Written | ✅ Passed | ✅ two-arg list + three-arg describe + Spark keys | ➖ notebook source |
| 5.1 | `tests/` | Full suite | — | — | ✅ 143 passed | — | — |

### Test Summary

- **Total tests written**: 10 (3 schema + 5 CORS + 2 notebook)
- **Total tests passing**: 143 (suite)
- **Layers used**: Unit (2 notebook), Integration (8 API)
- **Approval tests** (refactoring): Streamlit not modified; 1.3 locked existing empty-200 behavior
- **Pure functions created**: 1 (`_spark_column_to_http`)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `tests/test_api.py` | Modified | Schema + CORS TestClient tests |
| `tests/test_demo_notebook.py` | Created | Notebook arity/Spark-key contract |
| `app/main.py` | Modified | Correct list/describe arity, HTTP mapper, CORS regex |
| `app/models/response.py` | Modified | HTTP column contract comment only |
| `notebooks/01_demo.ipynb` | Modified | Two-/three-arg core; print col_name/data_type; iterate listed tables |
| `openspec/changes/fix-schema-surface/tasks.md` | Modified | All tasks `[x]` |

Unchanged: `app/core/schema.py` signatures; `ui/streamlit_app.py` expander keys.

## Deviations from Design

None — implementation matches design. Notebook describe iterates all listed tables (empty-safe) rather than hardcoding customer/lineitem only.

## Issues Found

None.

## Remaining Tasks

None.

## Workload / PR Boundary

- Mode: single local apply (no commit/PR)
- Current work unit: N/A (full change)
- Boundary: tasks 1.1–5.1
- Estimated review budget impact: Low (within 80–180 line forecast)

## pytest

`pytest tests/ -v` → **143 passed**
