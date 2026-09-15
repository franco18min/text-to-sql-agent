# Proposal: Fix Schema Surface

## Intent

`GET /schema`, the demo notebook, and CORS globs assume APIs that `app/core/schema.py` does not provide (`list_tables`/`describe_table` arity; Spark `col_name`/`data_type`). Starlette never matches `https://*.streamlit.app`. Align HTTP/notebook/CORS with real signatures without changing the agent schema layer.

## Scope

### In Scope
- Wire `GET /schema` to `list_tables(catalog, schema)` and `describe_table(catalog, schema, table)` using `settings.databricks_catalog` / `databricks_schema`
- Map DESCRIBE rows to HTTP `{name, type, nullable, comment}`; `table` = bare name; `full_name` = `{catalog}.{schema}.{table}`
- Keep Streamlit expander keys (`t["table"]`, `col.get("name")`/`type`)
- Fix notebook to two-/three-arg core calls and Spark print keys
- Replace CORS glob strings with `allow_origin_regex` plus exact localhost origins
- Mocked pytest for `GET /schema` (strict TDD)

### Out of Scope
- `schema.py` signature changes; retry loop; CI/Docker/docs/eval; Vector Search expansion; auth
- Changing Streamlit session keys; agent introspector; `fqdn_target_table` except as non-argument

## Capabilities

### New Capabilities
- `schema-http-api`: `GET /schema` adapter, column mapping, empty-list-on-`list_tables` failure, API tests
- `schema-demo-notebook`: notebook `list_tables`/`describe_table` arity and `col_name`/`data_type` display
- `api-cors-origins`: Starlette-compatible CORS regex for Streamlit Cloud / HF Spaces; credentials kept; localhost exact

### Modified Capabilities
None (`agent-retry-loop`, `schema-source-typing`, `sql-execution-limit`, `agent-run-latency` unchanged)

## Approach

Adapter at HTTP (explore #1 + CORS #4a). Core stays Spark-shaped. Mapper in `get_schema` only. Notebook documents core keys. CORS: `allow_origin_regex=r"https://.*\.(streamlit\.app|hf\.space)"` + `http://localhost:8501` / `127.0.0.1:8501`. Keep empty 200 if `list_tables` fails. Tests mock schema funcs: success mapping, empty on list failure.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/main.py` | Modified | Correct calls; column map; CORS regex |
| `app/models/response.py` | Modified | Comment/contract only unless typed columns added |
| `app/core/schema.py` | Unchanged | Consume only |
| `ui/streamlit_app.py` | Unchanged | Keys already HTTP-shaped |
| `notebooks/01_demo.ipynb` | Modified | Arity + Spark keys |
| `tests/test_api.py` | Modified | `GET /schema` mocks |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Dual column dialects | Med | Spec: core vs HTTP keys |
| Empty 200 hides outages | Med | Keep UX; log; spec it |
| Broad CORS regex | Low | Demo-only; keep credentials |
| Notebook JSON miss | Med | Cell-level review |

## Rollback Plan

Revert `main.py`, notebook, `test_api.py`. Agent/DDL paths unchanged.

## Dependencies

- Existing `databricks_catalog` / `databricks_schema`
- FastAPI CORSMiddleware `allow_origin_regex`

## Success Criteria

- [ ] `GET /schema` uses real `schema.py` signatures and maps `name`/`type`
- [ ] Streamlit schema browser works without key changes
- [ ] Notebook lists/describes without TypeError
- [ ] Deploy-style origins match via regex; localhost still exact
- [ ] Pytest covers success mapping and empty `list_tables` failure
