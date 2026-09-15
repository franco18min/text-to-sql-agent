# Proposal: Fix Agent Retry and Safety

## Intent

The LangGraph loop is wired for auto-correction but does not match the README: validators/executors never write `retry_history`, validation never increments `retry_count`, routers hardcode `3` instead of `settings.max_retries`, LIMIT is EXPLAIN-only, `run_agent` never sets `latency_ms`, and `AgentState.schema_source` omits introspector values (`show_describe`, VS fallback).

## Scope

### In Scope

- Append `retry_history` (`attempt`, `sql`, `error`) from validator and executor on failure
- Increment `retry_count` on validation failure; keep executor increment on execute failure
- Route give-up with `settings.max_retries` (not hardcoded 3)
- Persist LIMIT-capped `sql_query` before EXPLAIN/execute (`max_result_rows`)
- Measure `latency_ms` in `run_agent`
- Align `schema_source` Literal with API + introspector; normalize VS fallback to `show_describe` (do not expand Vector Search)
- Fix/add tests in `tests/test_agent.py` (history, increment, give-up, LIMIT on executed SQL, latency, `max_retries`)

### Out of Scope

GET `/schema`, UI keys, CI, Docker, gitignore, docs/eval numbers, screenshots, CORS, auth, streaming, BIRD, Vector Search expansion, new coordinator node, attaching unused `should_continue_after_retry`.

## Capabilities

Main `openspec/specs/` is empty. These are **new** full specs later (not deltas).

### New Capabilities

- `agent-retry-loop`: History writes, `retry_count` on validation+execute failure, routing via `settings.max_retries`, give-up after bound
- `sql-execution-limit`: Persist LIMIT-capped `sql_query` used for EXPLAIN and execute
- `agent-run-latency`: Wall-clock `latency_ms` on `run_agent` result
- `schema-source-typing`: `AgentState.schema_source` Literal matches API (`show_describe` | `cache` | `vector_search` | `none`); VS fallback normalized to `show_describe`

### Modified Capabilities

None

## Approach

Surgical node + edge fix (exploration approach 1). Keep current graph. Validator/executor append history and bump count. Routers read `settings.max_retries`. Validator persists `add_limit_if_missing`; executor applies the same helper before run. `run_agent` times invoke. Normalize fallback strings to `show_describe` (error elsewhere if needed). Apply with `strict_tdd: true`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/agent/nodes/sql_validator.py` | Modified | History, increment, persist capped SQL |
| `app/agent/nodes/executor.py` | Modified | History on fail; LIMIT before execute |
| `app/agent/edges.py` | Modified | `settings.max_retries` |
| `app/agent/graph.py` | Modified | `latency_ms` in `run_agent` |
| `app/agent/state.py` | Modified | `schema_source` Literal |
| `app/config.py` | Unchanged | Existing `max_retries` / `max_result_rows` |
| `tests/test_agent.py` | Modified | Loop, LIMIT, latency, settings tests |
| `app/models/response.py` | Unchanged | API Literal already correct |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Off-by-one vs old executor-only `>= 3` | Med | Spec: increment per failed validation/execute; give-up when `retry_count >= settings.max_retries` |
| Missed increment → recursion limit | Med | Both failure paths increment; tests for give-up |
| Fallback string vs Literal | Med | Normalize to `show_describe` |
| Tests assuming `latency_ms == 0` | Low | Update tests |

## Rollback Plan

Revert the listed agent/test files. Graph topology unchanged. Config keys already exist.

## Dependencies

- Existing `settings.max_retries`, `max_result_rows`, `add_limit_if_missing`
- Apply: RED-GREEN-REFACTOR (`strict_tdd: true`)

## Success Criteria

- [ ] Failed attempts expose prior SQL/error to the generator
- [ ] Invalid SQL give-up uses `settings.max_retries`, not LangGraph recursion
- [ ] Executed SQL includes LIMIT when missing
- [ ] `run_agent` returns non-zero `latency_ms` after a real invoke
- [ ] `schema_source` types accept `show_describe`; VS fallback does not emit free-form strings
