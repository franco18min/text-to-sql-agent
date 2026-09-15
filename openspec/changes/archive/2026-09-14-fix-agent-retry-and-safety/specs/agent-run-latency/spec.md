# agent-run-latency

### Requirement: run_agent sets latency_ms

`run_agent` MUST set `latency_ms` to elapsed milliseconds. After invoke it MUST be > 0.

#### Scenario: Success reports latency

- GIVEN a question that completes execute
- WHEN `run_agent` returns
- THEN `latency_ms` > 0

#### Scenario: Failure still reports latency

- GIVEN a run that give-ups after validate or execute failure
- WHEN `run_agent` returns
- THEN `latency_ms` > 0
