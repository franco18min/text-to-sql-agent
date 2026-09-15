# schema-source-typing

### Requirement: schema_source is a closed set

`schema_source` MUST be only `show_describe`, `cache`, `vector_search`, or `none`.

#### Scenario: show_describe is valid

- GIVEN schema from SHOW/DESCRIBE
- WHEN recorded
- THEN `schema_source` is `show_describe`

#### Scenario: Free-form source rejected

- GIVEN a value outside that set
- WHEN assigned as `schema_source`
- THEN type check rejects it

### Requirement: VS fallback is not a free-form error string

When Vector Search is unavailable and schema comes from SHOW/DESCRIBE, `schema_source` MUST be `show_describe`, not an exception string.

#### Scenario: VS fallback uses show_describe

- GIVEN Vector Search fails and schema loads via SHOW/DESCRIBE
- WHEN recorded
- THEN `schema_source` is `show_describe`

#### Scenario: Fallback is not exception text

- GIVEN Vector Search fails with an exception message
- WHEN recorded
- THEN `schema_source` is a closed-set member, not that message
