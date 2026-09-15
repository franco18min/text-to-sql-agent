# agent-retry-loop

### Requirement: Failures write retry_history

On validation or execution failure the agent MUST append `retry_history` with `attempt`, failed `sql`, and `error`. Next generate MUST see it.

#### Scenario: Validation failure records history

- GIVEN generated SQL that fails validation
- WHEN `run_agent` continues
- THEN history has `attempt`, that SQL, and non-empty `error`

#### Scenario: Execution failure records history

- GIVEN SQL that validates then fails execute
- WHEN `run_agent` continues
- THEN history has `attempt`, that SQL, and non-empty `error`

#### Scenario: Success leaves history empty

- GIVEN SQL that validates and executes
- WHEN `run_agent` finishes
- THEN `retry_history` is empty

### Requirement: Retry count increments on validation failure

Each validation failure MUST increment `retry_count` by one. Execute-failure increments MUST still occur.

#### Scenario: Validation failure increments count

- GIVEN `retry_count` is 0 and validation fails
- WHEN applied
- THEN `retry_count` is 1

#### Scenario: Execute failure still increments

- GIVEN validation passed and execute fails
- WHEN applied
- THEN `retry_count` is one greater than before execute

### Requirement: Bound is settings.max_retries then give-up

Ceiling MUST be `settings.max_retries` (MUST NOT hardcode 3). After failed validate or execute, next MUST be give-up if `retry_count >= settings.max_retries`, else generate.

#### Scenario: Custom max_retries stops the loop

- GIVEN `settings.max_retries` is 2 and every generate is invalid
- WHEN `run_agent` completes
- THEN give-up after two failed validations, not three

#### Scenario: At bound next step is give_up

- GIVEN `retry_count == settings.max_retries` after a failure
- WHEN routing
- THEN next is give-up

#### Scenario: Below bound the agent retries

- GIVEN `retry_count < settings.max_retries` after a failure
- WHEN routing
- THEN next is generate, not give-up
