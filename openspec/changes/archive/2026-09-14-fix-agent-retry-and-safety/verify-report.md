## Verification Report

**Change**: fix-agent-retry-and-safety
**Version**: N/A (new capabilities; main `openspec/specs/` empty)
**Mode**: Strict TDD

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 20 |
| Tasks complete | 20 |
| Tasks incomplete | 0 |

All `tasks.md` items 1.1–4.1 are `[x]`. `apply-progress.md` remaining: none.

### Build & Tests Execution
**Build**: ➖ Not configured (`openspec/config.yaml` `verify.build_command` is empty)

**Tests**: ✅ 49 passed / ❌ 0 failed / ⚠️ 0 skipped (`pytest tests/test_agent.py -v`)
```text
python -m pytest tests/test_agent.py -v --tb=short
======================== 49 passed, 1 warning in 4.38s ========================
```

**Full unit suite**: ✅ 133 passed / ❌ 0 failed (`pytest tests/ -v -m "not integration"`)
```text
python -m pytest tests/ -v -m "not integration" --tb=line
======================= 133 passed, 3 warnings in 4.44s =======================
(1 FutureWarning google.generativeai; 2 Pydantic Field name "schema" shadows)
```

**Coverage**: ➖ Not available in this interpreter
```text
python -m pytest tests/ --cov=app --cov-report=term-missing
ERROR: unrecognized arguments: --cov=app
```
Config lists pytest-cov; the active venv has no `--cov` plugin. Threshold 0. Not a test failure.

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Failures write retry_history | Validation failure records history | `tests/test_agent.py` > `TestSQLValidatorNode.test_validation_failure_records_history_and_increments` | ✅ COMPLIANT |
| Failures write retry_history | Execution failure records history | `tests/test_agent.py` > `TestExecutorNode.test_execution_failure_records_history_and_increments` | ✅ COMPLIANT |
| Failures write retry_history | Success leaves history empty | `tests/test_agent.py` > `TestSuccessLeavesHistoryEmpty.test_validate_and_execute_success_keeps_history_empty` | ✅ COMPLIANT |
| Retry count increments on validation failure | Validation failure increments count | `tests/test_agent.py` > `TestSQLValidatorNode.test_validation_failure_records_history_and_increments` | ✅ COMPLIANT |
| Retry count increments on validation failure | Execute failure still increments | `tests/test_agent.py` > `TestExecutorNode.test_execution_failure_increments_from_existing_count` | ✅ COMPLIANT |
| Bound is settings.max_retries then give-up | Custom max_retries stops the loop | `tests/test_agent.py` > `TestCustomMaxRetriesLoop.test_give_up_after_two_invalid_generations` | ✅ COMPLIANT |
| Bound is settings.max_retries then give-up | At bound next step is give_up | `tests/test_agent.py` > `TestGraphRouting.test_route_by_validation_at_custom_max_retries_is_give_up` (+ execution twin) | ✅ COMPLIANT |
| Bound is settings.max_retries then give-up | Below bound the agent retries | `tests/test_agent.py` > `TestGraphRouting.test_route_by_validation_below_custom_max_retries_retries` (+ execution twin) | ✅ COMPLIANT |
| Executed SQL is LIMIT-capped | Missing LIMIT added | `tests/test_agent.py` > `TestSqlExecutionLimit.test_missing_limit_persisted_with_settings_cap` | ✅ COMPLIANT |
| Executed SQL is LIMIT-capped | Oversize LIMIT capped | `tests/test_agent.py` > `TestSqlExecutionLimit.test_oversize_limit_capped_to_max_result_rows` | ✅ COMPLIANT |
| Executed SQL is LIMIT-capped | In-cap LIMIT kept | `tests/test_agent.py` > `TestSqlExecutionLimit.test_incap_limit_kept_without_extra_limit` | ✅ COMPLIANT |
| Executed SQL is LIMIT-capped | EXPLAIN matches execute SQL | `tests/test_agent.py` > `TestSqlExecutionLimit.test_explain_argument_equals_executed_sql` | ✅ COMPLIANT |
| run_agent sets latency_ms | Success reports latency | `tests/test_agent.py` > `TestAgentRunLatency.test_success_reports_positive_latency_ms` | ✅ COMPLIANT |
| run_agent sets latency_ms | Failure still reports latency | `tests/test_agent.py` > `TestAgentRunLatency.test_give_up_still_reports_positive_latency_ms` | ✅ COMPLIANT |
| schema_source is a closed set | show_describe is valid | `tests/test_agent.py` > `TestSchemaSourceTyping.test_show_describe_is_valid_literal` | ✅ COMPLIANT |
| schema_source is a closed set | Free-form source rejected | `tests/test_agent.py` > `TestSchemaSourceTyping.test_free_form_source_rejected` | ✅ COMPLIANT |
| VS fallback is not a free-form error string | VS fallback uses show_describe | `tests/test_agent.py` > `TestSchemaIntrospector.test_vs_fallback_uses_show_describe` | ✅ COMPLIANT |
| VS fallback is not a free-form error string | Fallback is not exception text | `tests/test_agent.py` > `TestSchemaIntrospector.test_vs_fallback_is_not_exception_text` | ✅ COMPLIANT |

**Compliance summary**: 18/18 scenarios compliant

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| retry_history + retry_count on validate fail | ✅ Implemented | `sql_validator_node` spreads `record_retry_failure` on static fail and EXPLAIN fail |
| retry_history + retry_count on execute fail | ✅ Implemented | `executor_node` except path; skip path does not increment/append |
| Success does not append history | ✅ Implemented | Success returns omit `retry_history` (LangGraph merge keeps `[]`) |
| Routers use `settings.max_retries` | ✅ Implemented | `route_by_validation` and `route_by_execution` |
| LIMIT persist + recap | ✅ Implemented | `cap_sql_query` in validator then executor |
| `run_agent` latency_ms | ✅ Implemented | `time.perf_counter` around `graph.invoke`; return dict only |
| schema_source Literal | ✅ Implemented | `AgentState` closed set; VS except `source = "show_describe"` |
| `response.py` unchanged Literal | ✅ Implemented | Matches design; not expanded |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Nodes write; edges route | ✅ Yes | No coordinator node |
| History `{attempt, sql, error}` post-increment | ✅ Yes | `record_retry_failure` |
| `retry_count >= settings.max_retries` | ✅ Yes | Both live routers |
| LIMIT both validator + executor | ✅ Yes | `cap_sql_query` |
| Latency wrap `run_agent` only | ✅ Yes | Graph state `latency_ms` not patched |
| VS fallback `"show_describe"` | ✅ Yes | |
| Leave `should_continue_after_retry` unwired | ✅ Yes | Still `>= 3`; not in `build_graph` |
| Extract helpers | ✅ Yes | `app/agent/retry.py`, `app/agent/sql_limit.py` (design table listed node files; extract is 2.8/3.8 refactor) |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | Found in `apply-progress.md` TDD Cycle Evidence |
| All tasks have tests | ✅ | 20/20 tasks point at `tests/test_agent.py` (or N/A verify 4.1) |
| RED confirmed (tests exist) | ✅ | Test file exists; 49 functions collected |
| GREEN confirmed (tests pass) | ✅ | 49/49 `test_agent.py` pass; 133/133 suite pass |
| Triangulation adequate | ✅ | Retry fail paths 3+; LIMIT 4 scenarios; both routers; latency success+give-up; VS two messages |
| Safety Net for modified files | ✅ | Apply-progress records safety nets on modified nodes; 2.7 N/A success path already empty |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 133 | 3 (`test_agent.py`, `test_api.py` TestClient, `test_sql_safety.py`) | pytest + unittest.mock |
| Integration | 0 marked | 0 | pytest marker `integration` declared, unused |
| E2E | 0 | 0 | not installed |
| **Total** | **133** | **3** | |

This change’s new/extended cases live in `tests/test_agent.py` (49 tests, mocked LLM/DB). `TestCustomMaxRetriesLoop` is a mocked graph walk, not live Databricks.

---

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected in the active interpreter (`pytest --cov` unrecognized). Config claims pytest-cov; it is not loaded here.

---

### Assertion Quality
| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| `tests/test_agent.py` | 191–192 | `assert "LIMIT 1000" in add_limit_if_missing(...)` | Leftover `test_limit_added_when_missing` never asserts validator/executor persist; real LIMIT coverage is `TestSqlExecutionLimit` | WARNING |
| `tests/test_agent.py` | 576–580 | `inspect.getsource` / `"should_continue_after_retry" not in graph_src` | Implementation-detail coupling (source text), not runtime graph wiring API | WARNING |

**Assertion quality**: 0 CRITICAL, 2 WARNING

No tautologies, ghost loops, or assertion-without-production-call in the new scenario tests. Latency tests mock `perf_counter` but still call `run_agent` and assert elapsed milliseconds.

---

### Quality Metrics
**Linter**: ➖ Not available (`python -m ruff` / `ruff` not on PATH in this shell)
**Type Checker**: ➖ Not available (config: no mypy/pyright)

### Issues Found
**CRITICAL**: None
**WARNING**:
- `TestSQLValidatorNode.test_limit_added_when_missing` still checks `add_limit_if_missing` in isolation; does not prove persisted `sql_query` (superseded by `TestSqlExecutionLimit`).
- `test_should_continue_after_retry_still_hardcoded_and_unwired` couples to source text; dead helper still hardcodes `3` (allowed by design).
- pytest-cov and ruff not executable in the verification venv; changed-file coverage and lint not measured this run.

**SUGGESTION**:
- Optional later: delete or rewrite `test_limit_added_when_missing`; wire or remove `should_continue_after_retry`.
- Critical business loop is unit/mocked-graph only; FastAPI TestClient exists but was out of scope.

### Verdict
**PASS WITH WARNINGS**
18/18 spec scenarios have passing covering tests; 49 + 133 pytest green; leftover isolated LIMIT test, dead hardcoded helper, and missing cov/ruff in this venv are warnings only.
