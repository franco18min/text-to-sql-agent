# schema-http-api Specification

## Purpose

`GET /schema` lists and describes tables for the UI using the HTTP column contract.

## Requirements

### Requirement: Catalog-scoped listing

`GET /schema` MUST list tables in the configured catalog and schema, then describe each table. Core schema signatures MUST NOT change. The response MUST be HTTP 200.

#### Scenario: Success

- GIVEN catalog/schema with tables and describe rows
- WHEN a client calls `GET /schema`
- THEN each table has `catalog`, `schema`, `table` (bare name), and `full_name` `{catalog}.{schema}.{table}`

#### Scenario: Listing failure

- GIVEN listing fails
- WHEN a client calls `GET /schema`
- THEN HTTP 200 with an empty table list

### Requirement: HTTP column keys

Columns MUST use `name`, `type`, `nullable`, `comment` (not Spark describe keys). Missing comments MAY be empty.

#### Scenario: Mapping

- GIVEN describe rows with name, type, nullability, optional comment
- WHEN `GET /schema` succeeds
- THEN each column includes `name` and `type`, plus `nullable` and `comment` present or empty

### Requirement: Streamlit keys unchanged

Streamlit MUST keep reading `table`, `name`, and `type`. UI keys MUST NOT change.

#### Scenario: Browser render

- GIVEN the HTTP contract
- WHEN the schema browser expands a table
- THEN names and types show without UI changes

### Requirement: API tests

Tests MUST mock externals and cover success mapping plus empty list on listing failure.

#### Scenario: Happy test

- GIVEN mocked listing and describe success
- WHEN tests call `GET /schema`
- THEN they assert HTTP keys and `full_name`

#### Scenario: Failure test

- GIVEN mocked listing failure
- WHEN tests call `GET /schema`
- THEN they assert 200 and empty tables
