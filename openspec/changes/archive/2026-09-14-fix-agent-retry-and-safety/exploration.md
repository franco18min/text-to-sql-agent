## Exploration: fix-agent-retry-and-safety

### Current State

The LangGraph graph (`sql_generator` → `sql_validator` → `executor`, with conditional retry edges) is wired for auto-correction, but the loop is incomplete.

**Retry history (confirmed):** `AgentState.retry_history` is initialized empty and formatted into `SQL_GENERATOR_PROMPT` by `sql_generator_node`. No node appends to it. `sql_validator_node` and `executor_node` never write `retry_history`. Retries always see `(first attempt)`, so the LLM gets no prior SQL/error.

**Retry count / give-up (confirmed):** Only `executor_node` increments `retry_count` (+1 on execute exception). `sql_validator_node` never increments. `route_by_validation` and `route_by_execution` use hardcoded `retry_count >= 3`, not `settings.max_retries`. Tests pass `max_retries` in the routing dict, but that key is not on `AgentState` and is unused. Invalid SQL therefore loops `sql_generator` ↔ `sql_validator` until LangGraph’s recursion limit. `should_continue_after_retry` exists in `edges.py` and is not attached in `build_graph`.

**LIMIT 1000 (confirmed):** `add_limit_if_missing` is applied only to the EXPLAIN string. The validator does not write `sql_query` back. `executor_node` runs `state["sql_query"]` raw. `test_limit_added_when_missing` re-calls `add_limit_if_missing` itself; it does not assert graph state.

**latency_ms (confirmed):** `run_agent` never times the invoke; it returns `final.get("latency_ms", 0.0)`. `POST /query` falls back to wall clock (`or wall_ms`), so the HTTP chip can still show latency. Memory/eval paths that read agent state still get 0.

**schema_source (confirmed):** `AgentState` Literal is `"vector_search"|"information_schema"|"cache"`. Introspector returns `"show_describe"`, `"vector_search"`, or a long `"show_describe_fallback (vs_error: …)"` string. API `AgentResponse.schema_source` already allows `"show_describe"|"cache"|"vector_search"|"none"`.

Out of scope remains: GET /schema, UI column keys, CI, Docker, gitignore, docs/eval numbers, screenshots, CORS, Vector Search, auth, streaming.

### Affected Areas
- `app/agent/nodes/sql_validator.py` — must increment retries, append history, persist capped SQL
- `app/agent/nodes/executor.py` — history on fail; optional LIMIT on execute
- `app/agent/edges.py` — use `settings.max_retries`; dead `should_continue_after_retry`
- `app/agent/graph.py` — set `latency_ms` in `run_agent`
- `app/agent/state.py` — align `schema_source` Literal with introspector + API
- `app/agent/nodes/sql_generator.py` — already consumes history; no write
- `app/config.py` — `max_retries` / `max_result_rows` already exist
- `tests/test_agent.py` — routing tests ignore settings; LIMIT test is tautological; no history/loop tests
- `app/models/response.py` — API Literal already has `show_describe` (align state, not reinvent API)
- `app/api/chat.py` — wall-clock fallback; no change required if `run_agent` sets latency

### Approaches
1. **Surgical node + edge fix** — Validator/executor write `retry_history` (`attempt`, `sql`, `error`), increment `retry_count` on validation failure (and keep executor increment on execute failure), persist `sql_query` after `add_limit_if_missing` (executor may apply the same helper), route with `settings.max_retries`, time `run_agent`, widen `schema_source` to include `show_describe` (and a stable fallback token, not a free-form error string).
   - Pros: Matches README/architecture; smallest surface; uses existing settings; TDD-friendly
   - Cons: Must define off-by-one (count vs attempts); fallback source string may still violate Literal unless normalized
   - Effort: Low

2. **Dedicated retry coordinator node** — Insert a node after validator/executor failures that centralizes increment, history, and routing.
   - Pros: Single place for loop policy
   - Cons: Extra graph node; unused `should_continue_after_retry` already shows over-design; larger test rewrite
   - Effort: Medium

3. **Edges-only cap (no history / no LIMIT persist)** — Only `retry_count` bump + `max_retries` in routers.
   - Pros: Stops recursion loops quickly
   - Cons: Auto-correction still blind; LIMIT still missing at execute; latency/schema_source remain wrong
   - Effort: Low (incomplete)

### Recommendation
Use **Approach 1**. The advertised loop is already in the graph; the bugs are missing writes and hardcoded thresholds. Persist capped SQL from the validator (and/or executor) so LIMIT is a runtime guardrail, not an EXPLAIN-only rewrite. Measure latency in `run_agent`. Align `AgentState.schema_source` with the introspector and API; normalize VS fallback to `show_describe` plus a separate error field if needed—do not expand Vector Search.

Tests to add/fix in `tests/test_agent.py`: validation failure increments `retry_count` and appends `retry_history`; after `max_retries` route is `give_up`; executor runs SQL that includes LIMIT; `run_agent` returns non-zero `latency_ms` (mock graph); routing uses `settings.max_retries` not a magic 3. Honor `strict_tdd: true` at apply time.

### Risks
- Off-by-one: `>= 3` after executor-only increments currently allows two failed executes then give-up; adding validator increments changes how many LLM regenerations occur.
- Recursion limit vs give_up: if increment is missed on one path, loops can still hit LangGraph recursion.
- `schema_source` fallback string can break Pydantic `Literal` on `/query` if VS fails.
- API latency already uses wall clock; tests that assume `latency_ms == 0` from `run_agent` may need updates.
- Engram MCP unavailable this session; OpenSpec file is the persistence.

### Ready for Proposal
Yes — scope is five confirmed bugs in the agent loop/metadata. Orchestrator can tell the user the auto-correction graph exists but does not write feedback, does not stop validation retries, does not apply LIMIT at execute, does not record agent latency, and types `schema_source` incorrectly. Next phase: `sdd-propose`.
