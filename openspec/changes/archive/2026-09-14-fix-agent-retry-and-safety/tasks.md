# Tasks: Fix Agent Retry and Safety

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 320–450 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 retry loop → PR 2 LIMIT/latency/schema |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | History, `retry_count`, `settings.max_retries` routing | PR 1 | Base tracker/main; `tests/test_agent.py` retry scenarios |
| 2 | LIMIT persist, `latency_ms`, `schema_source` Literal | PR 2 | Base = PR 1 branch if feature-chain |

## Phase 1: Foundation (RED types/config use)

- [x] 1.1 RED `tests/test_agent.py`: `get_type_hints`/`schema_source` assignment rejects free-form; `show_describe` valid (`schema-source-typing`: show_describe is valid, Free-form source rejected).
- [x] 1.2 GREEN `app/agent/state.py`: `schema_source: Literal["show_describe","cache","vector_search","none"]`.
- [x] 1.3 REFACTOR Literal only; keep `app/models/response.py` unchanged.

## Phase 2: Retry loop (TDD)

- [x] 2.1 RED `tests/test_agent.py`: `sql_validator_node` invalid SQL → history `{attempt,sql,error}` non-empty error, `retry_count==1` (Validation failure records history / increments count).
- [x] 2.2 GREEN `app/agent/nodes/sql_validator.py`: on fail copy `retry_history`, append post-increment attempt, `retry_count+1`; skip success writes.
- [x] 2.3 RED `tests/test_agent.py`: `executor_node` `sql_valid` True, mock `execute_query` raise → history + count+1; skip path no increment (Execution failure records history / Execute failure still increments).
- [x] 2.4 GREEN `app/agent/nodes/executor.py`: fail append+increment; skip (`sql_valid` false) unchanged.
- [x] 2.5 RED `tests/test_agent.py`: patch `settings.max_retries`; `route_by_*` at-bound `give_up`, below-bound generate; graph invalid generate give-up after 2 (`Custom max_retries` / At bound / Below bound).
- [x] 2.6 GREEN `app/agent/edges.py`: both routers `retry_count >= settings.max_retries`; leave `should_continue_after_retry` unwired.
- [x] 2.7 RED/GREEN happy path `retry_history==[]` (Success leaves history empty).
- [x] 2.8 REFACTOR validator/executor history helper if duplicated; `app/config.py` unused.

## Phase 3: LIMIT, latency, introspector

- [x] 3.1 RED `tests/test_agent.py`: missing/oversize/in-cap LIMIT; EXPLAIN arg equals execute SQL (`sql-execution-limit` four scenarios).
- [x] 3.2 GREEN `sql_validator.py`: success persist `add_limit_if_missing(..., settings.max_result_rows)` then EXPLAIN that string.
- [x] 3.3 GREEN `executor.py`: cap again before `execute_query`.
- [x] 3.4 RED `tests/test_agent.py`: patch `build_graph`/`invoke`; `run_agent` success and give-up `latency_ms>0` (`agent-run-latency`).
- [x] 3.5 GREEN `app/agent/graph.py`: `time.perf_counter` around `invoke`; set return `latency_ms` only.
- [x] 3.6 RED `tests/test_agent.py`: mock VS raise → `schema_source=="show_describe"` not exception text (`VS fallback` / Fallback is not exception text).
- [x] 3.7 GREEN `app/agent/nodes/schema_introspector.py`: VS except `source="show_describe"`.
- [x] 3.8 REFACTOR LIMIT helper calls; no new coordinator.

## Phase 4: Verify

- [x] 4.1 `pytest tests/test_agent.py -v` (fast: `pytest tests/ -v -m "not integration"`).
