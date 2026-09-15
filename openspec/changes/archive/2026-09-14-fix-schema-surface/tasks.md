# Tasks: Fix Schema Surface

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
| 1 | HTTP mapper, CORS regex, notebook arity, API tests | PR 1 | Single PR to default branch; tests/docs in-slice |

## Phase 1: RED — API tests (`schema-http-api`)

- [x] 1.1 In `tests/test_api.py`, add failing TestClient test: patch `app.core.schema.list_tables`/`describe_table`; `GET /schema` 200; assert `catalog`, `schema`, bare `table`, `full_name` `{catalog}.{schema}.{table}` (Success, Happy test).
- [x] 1.2 Same file: failing test mapping Spark `col_name`/`data_type`/`nullable`/`comment` → HTTP `name`/`type`/`nullable`/`comment`; missing comment → `""` (Mapping).
- [x] 1.3 Same file: failing test listing raises → 200 and `tables=[]` (Listing failure, Failure test).

## Phase 2: GREEN — HTTP adapter (`app/main.py`, `app/models/response.py`)

- [x] 2.1 Implement `get_schema`: `list_tables(settings.databricks_catalog, settings.databricks_schema)`; on failure log warning and empty 200; else `describe_table(catalog, schema, table)` per bare name; map columns in handler only; do not change `app/core/schema.py`.
- [x] 2.2 Build HTTP `{catalog, schema, table, full_name, columns}`; keep `SchemaResponse` `list[dict]`; comment contract in `app/models/response.py`.
- [x] 2.3 Confirm `ui/streamlit_app.py` still uses `t["table"]` and `col.get("name")`/`type` (Browser render); no UI edit.
- [x] 2.4 REFACTOR mapper only if tests stay green.

## Phase 3: CORS (`api-cors-origins`)

- [x] 3.1 RED optional: TestClient OPTIONS/GET with Origin `https://foo.streamlit.app`, `https://bar.hf.space`, `http://localhost:8501`, `http://127.0.0.1:8501` (CORS scenarios).
- [x] 3.2 GREEN `app/main.py`: `allow_origins` exact localhost/127.0.0.1:8501; `allow_origin_regex=r"https://.*\.(streamlit\.app|hf\.space)"`; drop glob strings; keep `allow_credentials=True`.
- [x] 3.3 REFACTOR CORS block; pytest green.

## Phase 4: Notebook (`schema-demo-notebook`)

- [x] 4.1 `notebooks/01_demo.ipynb`: `list_tables(catalog, schema)` two-arg (Tables listed); no concatenated FQDN arg.
- [x] 4.2 `notebooks/01_demo.ipynb`: `describe_table("samples","tpch", table)` three-arg; print `col_name`/`data_type` (Types displayed); empty list does not crash (Empty listing).

## Phase 5: Verify

- [x] 5.1 `pytest tests/ -v` (or `tests/test_api.py`); ruff optional on `app/` `tests/`.
