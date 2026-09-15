## Exploration: GET /schema, Streamlit schema browser, demo notebook, CORS

### Current State

`app/core/schema.py` is the agent-facing contract and is used correctly by `schema_introspector.py`: `list_tables(catalog, schema) -> list[str]` (bare table names from `SHOW TABLES`) and `describe_table(catalog, schema, table) -> list[dict]` with Spark DESCRIBE keys `col_name`, `data_type`, `comment`, `nullable`.

`GET /schema` in `app/main.py` does **not** match that contract. It calls `list_tables(settings.fqdn_target_table)` where `fqdn_target_table` is `"catalog.schema"` (one string). `SHOW TABLES IN {catalog}.{schema}` then becomes `SHOW TABLES IN samples.tpch.{undefined}` / a TypeError on the second positional arg. The loop then treats each table as `t["full_name"]` / `t["catalog"]` / `t["schema"]` / `t["table"]` — dicts that `list_tables` never returns. `describe_table(t["full_name"])` is one argument vs three required. Failures on `list_tables` currently return empty `SchemaResponse` (200) instead of 500.

`SchemaTableInfo.columns` is `list[dict]` with a comment documenting `[{name, type, nullable, comment}, ...]`. Pydantic does not validate those keys. Core `describe_table` emits `col_name`/`data_type`, so even a correctly wired endpoint would ship Spark keys unless mapped.

`ui/streamlit_app.py` expander uses `t["table"]` and `col.get("name")` / `col.get("type")` — aligned with the **API comment**, not with core DESCRIBE keys. Nested expanders and `st.session_state._schema` are otherwise fine.

`notebooks/01_demo.ipynb` repeats the broken FQDN/`t['full_name']` listing and `describe_table("samples.tpch.customer")` plus `col['name']`/`col['type']`.

CORS `allow_origins` includes literal `"https://*.streamlit.app"` and `"https://*.hf.space"`. Starlette/FastAPI match origins with exact string equality (plus a special `*` case). Those globs never match. Current Streamlit UI uses server-side `requests`, so CORS is not on the hot path for local Streamlit; it still fails for browser clients and the deploy comment in `main.py`. `allow_credentials=True` forbids origin `*`.

`tests/test_api.py` covers `/health`, `/query`, sessions — **no GET /schema**. No tests for CORS. `openspec/specs/` has no schema HTTP/UI spec (only `schema-source-typing` for agent metadata). Config `strict_tdd: true`.

`settings.databricks_catalog` / `databricks_schema` are the right split; `fqdn_target_table` is a display shortcut, not a `list_tables` argument.

### Affected Areas

- `app/main.py` — `get_schema` call sites; CORS `allow_origins` globs
- `app/models/response.py` — `SchemaTableInfo.columns` contract (`name`/`type` vs `col_name`/`data_type`)
- `app/core/schema.py` — **do not change signatures** (agent + DDL already correct); consume only
- `app/config.py` — `fqdn_target_table` vs catalog/schema fields (read-only unless docs)
- `ui/streamlit_app.py` — schema expander keys; works once API maps to `name`/`type`
- `notebooks/01_demo.ipynb` — `list_tables`/`describe_table` arity and print keys
- `tests/test_api.py` — missing GET `/schema` (and optional CORS) tests
- `app/agent/nodes/schema_introspector.py` — coupling constraint: keep core signatures

Out of scope (per request): retry loop, CI, Docker, gitignore, eval docs, screenshots, Vector Search expansion, auth.

### Approaches

1. **Adapter at GET /schema (keep core Spark-shaped)** — `list_tables(settings.databricks_catalog, settings.databricks_schema)`; `describe_table(catalog, schema, name)`; map columns to `{name, type, nullable, comment}`; notebook uses the same three-arg core API and Spark keys **or** prints mapped keys; CORS via `allow_origin_regex` (plus exact localhost); TDD tests mock `list_tables`/`describe_table`.
   - Pros: Agent/DDL untouched; matches `SchemaTableInfo` comment and Streamlit; smallest blast radius
   - Cons: Two column-key dialects (core vs HTTP) must stay documented
   - Effort: Low

2. **Normalize column keys inside `describe_table` to `name`/`type`** — change core + `build_table_ddl` + any tests of DDL comments.
   - Pros: One dict shape everywhere
   - Cons: Touches LLM context builder; extra risk vs archived retry/schema-source work; notebook/API still need arity fix
   - Effort: Medium

3. **Widen `list_tables`/`describe_table` to accept FQDN or catalog+schema** — wrappers or overloads so current `main.py`/notebook calls work.
   - Pros: Call sites could stay FQDN-shaped
   - Cons: Ambiguous `SHOW TABLES IN` parsing; agent already uses two args; UI still needs HTTP `name`/`type`; more API surface
   - Effort: Medium

4. **CORS: regex vs explicit list vs `allow_origin_regex` only for known hosts**
   - **4a** `allow_origin_regex=r"https://.*\.(streamlit\.app|hf\.space)"` plus exact localhost — matches Starlette; keep credentials
   - **4b** Drop wildcard deploy origins; localhost only until real hosts known — simplest, weaker deploy story
   - Effort: Low

### Recommendation

**Approach 1 + 4a.** Treat `app.core.schema` as the Spark/agent layer. Fix `get_schema` as a thin mapper onto `SchemaTableInfo` (`table` = bare name, `full_name` = `{catalog}.{schema}.{table}`, `columns` with `name`/`type`). Leave Streamlit expander keys as-is. Fix the notebook to `list_tables(catalog, schema)` (iterate strings) and `describe_table("samples", "tpch", "customer")` using `col_name`/`data_type` **or** a tiny local mapper — prefer Spark keys in the notebook so it documents the core module honestly. Replace origin globs with `allow_origin_regex` and keep `http://localhost:8501` / `127.0.0.1:8501` in `allow_origins`. Add mocked `GET /schema` tests (success mapping + empty on `list_tables` failure if that UX is kept). Do not change `schema.py` signatures.

### Risks

- Empty 200 on `list_tables` failure hides Databricks outages in the schema browser (existing UX; decide in spec whether to keep)
- Dual column-key dialects (`col_name`/`data_type` vs `name`/`type`) if later callers copy the wrong layer
- CORS regex too broad (`https://evil.streamlit.app` style) — acceptable for demo; tighten if credentials stay on
- Nested Streamlit expanders inside sidebar expander can be awkward UX; not a contract bug
- Notebook JSON cell edits are easy to miss in review
- Engram MCP unavailable this session; artifact is filesystem-only (openspec mode)

### Ready for Proposal

Yes. Orchestrator should run **sdd-propose** for `fix-schema-surface`: HTTP adapter + column mapping + notebook arity/keys + CORS regex + pytest for GET `/schema`. Do not reopen retry loop or Vector Search.
