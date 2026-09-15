# schema-demo-notebook Specification

## Purpose

The demo notebook lists tables and shows column types using the real listing/describe contract.

## Requirements

### Requirement: Listing succeeds

The notebook MUST list tables for the configured catalog and schema (two arguments). It MUST NOT pass a single concatenated name.

#### Scenario: Tables listed

- GIVEN a reachable catalog and schema
- WHEN the listing cell runs
- THEN table names appear and no arity error is raised

### Requirement: Column types succeed

Describe MUST use catalog, schema, and table. Printed columns MUST use Spark keys `col_name` and `data_type`, not HTTP `name`/`type`.

#### Scenario: Types displayed

- GIVEN at least one listed table
- WHEN describe runs
- THEN each column name and type is visible without arity or missing-key errors

#### Scenario: Empty listing

- GIVEN no tables
- WHEN the notebook continues
- THEN empty listing MUST NOT crash the notebook
