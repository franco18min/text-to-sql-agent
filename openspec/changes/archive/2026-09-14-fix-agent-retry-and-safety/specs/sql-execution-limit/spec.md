# sql-execution-limit

### Requirement: Executed SQL is LIMIT-capped

MUST persist `sql_query` used for EXPLAIN and execute. Missing LIMIT MUST become `settings.max_result_rows`. LIMIT above the cap MUST be reduced to it; LIMIT at or below MUST be kept (no extra LIMIT). EXPLAIN MUST use the same persisted `sql_query` as execute.

#### Scenario: Missing LIMIT added

- GIVEN SQL with no LIMIT and `settings.max_result_rows` is N
- WHEN execute runs
- THEN executed SQL contains `LIMIT N`

#### Scenario: Oversize LIMIT capped

- GIVEN SQL with LIMIT greater than `settings.max_result_rows`
- WHEN EXPLAIN or execute runs
- THEN persisted LIMIT equals `settings.max_result_rows`

#### Scenario: In-cap LIMIT kept

- GIVEN SQL with LIMIT at or below `settings.max_result_rows`
- WHEN EXPLAIN or execute runs
- THEN that LIMIT is kept with no extra LIMIT

#### Scenario: EXPLAIN matches execute SQL

- GIVEN SQL that needed LIMIT add or cap
- WHEN EXPLAIN and execute run
- THEN both use the same persisted `sql_query`
