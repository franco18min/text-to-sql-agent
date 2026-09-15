# apply-progress: fix-agent-retry-and-safety

**Mode**: Strict TDD  
**Workload**: size:exception accepted; Work Unit 1 (1.1–2.8) + Work Unit 2 (3.1–4.1)  
**Batch**: no git commits / PRs  

## Completed Tasks

- [x] 1.1 RED schema_source Literal tests
- [x] 1.2 GREEN AgentState Literal
- [x] 1.3 REFACTOR Literal only; response.py unchanged
- [x] 2.1 RED validator history/count
- [x] 2.2 GREEN validator fail writes
- [x] 2.3 RED executor history/count + skip
- [x] 2.4 GREEN executor fail writes; skip unchanged
- [x] 2.5 RED settings.max_retries routing + graph give-up after 2
- [x] 2.6 GREEN edges use settings.max_retries; should_continue_after_retry unwired
- [x] 2.7 RED/GREEN success leaves retry_history empty
- [x] 2.8 REFACTOR record_retry_failure helper; config.py unused
- [x] 3.1 RED LIMIT persist / EXPLAIN=execute / in-cap / oversize
- [x] 3.2 GREEN validator persists `cap_sql_query(..., settings.max_result_rows)` then EXPLAIN
- [x] 3.3 GREEN executor recaps before `execute_query`
- [x] 3.4 RED `run_agent` latency success + give-up
- [x] 3.5 GREEN `time.perf_counter` around `invoke`; return `latency_ms` only
- [x] 3.6 RED VS fallback `schema_source=="show_describe"`
- [x] 3.7 GREEN introspector except uses `"show_describe"`
- [x] 3.8 REFACTOR `cap_sql_query`; no new coordinator
- [x] 4.1 `pytest tests/test_agent.py -v` (49 passed); `pytest tests/ -v -m "not integration"` (133 passed)

## Remaining

None — all tasks 1.1–4.1 complete. Ready for sdd-verify.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_agent.py` | Unit | ✅ 18/18 | ✅ Written | ✅ Passed | ✅ 2 cases | ➖ tests only |
| 1.2 | `tests/test_agent.py` | Unit | ✅ 18/18 | ✅ 1.1 | ✅ Literal change | ✅ closed set + free-form | ➖ None needed |
| 1.3 | `tests/test_agent.py` | Unit | N/A | ➖ type-only | ✅ response.py untouched | ➖ Single | ✅ Literal only |
| 2.1 | `tests/test_agent.py` | Unit | ✅ validator 3/3 | ✅ Written | ✅ Passed | ✅ DROP + INSERT + EXPLAIN | ➖ |
| 2.2 | `tests/test_agent.py` | Unit | ✅ | ✅ 2.1 | ✅ Passed | ✅ 3 fail paths | later 2.8 |
| 2.3 | `tests/test_agent.py` | Unit | ✅ 18+new | ✅ Written | ✅ Passed | ✅ fail + skip + existing count | ➖ |
| 2.4 | `tests/test_agent.py` | Unit | ✅ | ✅ 2.3 | ✅ Passed | ✅ skip vs fail | later 2.8 |
| 2.5 | `tests/test_agent.py` | Unit + graph | ✅ routing 8/8 | ✅ Written | ✅ Passed | ✅ at-bound + below-bound + graph max=2 | ➖ |
| 2.6 | `tests/test_agent.py` | Unit | ✅ | ✅ 2.5 | ✅ Passed | ✅ both routers | ➖ leave unwired helper |
| 2.7 | `tests/test_agent.py` | Unit | N/A (success path already empty) | ✅ Written (already green: success never wrote history) | ✅ Passed | ✅ merge path + no write on success | ➖ None needed |
| 2.8 | `tests/test_agent.py` | Unit | ✅ 36 before helper | ✅ helper ImportError | ✅ Passed | ✅ first fail + copy history | ✅ extracted `record_retry_failure` |
| 3.1 | `tests/test_agent.py` | Unit | ✅ 38/38 | ✅ Written (KeyError `sql_query`; executor still ran LIMIT 5000) | ✅ Passed | ✅ missing + oversize + in-cap + EXPLAIN=execute | ➖ |
| 3.2 | `tests/test_agent.py` | Unit | ✅ | ✅ 3.1 | ✅ Passed | ✅ N=50 / 200 / 7 kept | later 3.8 |
| 3.3 | `tests/test_agent.py` | Unit | ✅ | ✅ 3.1 executor recap | ✅ Passed | ✅ recap oversize + EXPLAIN match | later 3.8 |
| 3.4 | `tests/test_agent.py` | Unit | ✅ graph give-up still green | ✅ Written (`latency_ms` 0.0 vs 40/12) | ✅ Passed | ✅ success 40ms + give-up 12ms | ➖ pytest.approx for float |
| 3.5 | `tests/test_agent.py` | Unit | ✅ | ✅ 3.4 | ✅ Passed | ✅ two elapsed values | ➖ None needed |
| 3.6 | `tests/test_agent.py` | Unit | ✅ `test_builds_schema_context` | ✅ Written (`show_describe_fallback (vs_error: ...)`) | ✅ Passed | ✅ show_describe + not exception text | ➖ |
| 3.7 | `tests/test_agent.py` | Unit | ✅ | ✅ 3.6 | ✅ Passed | ✅ two exception messages | ➖ unused `as e` dropped |
| 3.8 | `tests/test_agent.py` | Unit | ✅ LIMIT tests as approval | ✅ `cap_sql_query` missing/oversize | ✅ Passed | ✅ 2 helper cases + node patches | ✅ `app/agent/sql_limit.py` |
| 4.1 | `tests/test_agent.py` + `tests/` | Unit | N/A | N/A verify | ✅ 49 + 133 passed | N/A | N/A |

### Test Summary
- **Total tests written this batch**: 11 new in `test_agent.py` (49 vs Work Unit 1 baseline 38)
- **Total tests passing**: 49 in `tests/test_agent.py`; 133 in `tests/ -m "not integration"`
- **Layers used**: Unit (this batch), Integration/graph (prior), E2E (0)
- **Approval tests**: LIMIT node tests reused for 3.8 extract
- **Pure functions created**: 1 this batch (`cap_sql_query`); prior `record_retry_failure`

## Deviations
None — implementation matches design. Engram `mem_save` skipped: `user-engram` MCP namespace in error state.

## Workload / PR Boundary
- Mode: size:exception
- Current work unit: 2 (tasks 3.1–4.1)
- Boundary: after Phase 1–2 retry loop; LIMIT persist + latency + VS fallback + pytest
- Estimated review budget impact: remaining delta is LIMIT/latency/schema only; exception already accepted
