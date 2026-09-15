# recruiter-agent-facts Specification

## Purpose

Facts MUST match shipped code.

## Requirements

### Requirement: EXPLAIN Dry-Run Described

`README.md`, talking-points, and `docs/architecture.md` MUST describe SQL **EXPLAIN** dry-run.

#### Scenario: EXPLAIN mentioned

- GIVEN README, `docs/interview-talking-points.md`, and `docs/architecture.md`
- WHEN read
- THEN each MUST mention EXPLAIN or equivalent dry-run

### Requirement: No Zero-Row Retry Claim

Docs MUST NOT claim retry on **0 rows**. Retry MUST be **exception-only**.

#### Scenario: Zero-row retry absent

- GIVEN README, `docs/interview-talking-points.md`, and `docs/architecture.md`
- WHEN scanned for retry
- THEN they MUST NOT state retry on empty results
- AND MUST describe retry only on exceptions or errors

### Requirement: Notebook Exists Not Placeholder

README or tree MUST list `notebooks/01_demo.ipynb` as a real notebook.

#### Scenario: Notebook path and file

- GIVEN the repo
- WHEN README or tree is read
- THEN it MUST list that path AND the file MUST exist as a notebook

### Requirement: Version 1.0.0

README MUST present version **1.0.0**.

#### Scenario: Version text

- GIVEN `README.md`
- WHEN read
- THEN it MUST display 1.0.0

### Requirement: Unused Schema Prompt Optional

Docs MAY footnote unused `SCHEMA_RETRIEVAL_PROMPT`. They MUST NOT imply active Vector Search.

#### Scenario: Optional footnote honesty

- GIVEN that prompt is mentioned
- WHEN present
- THEN it MUST be labeled unused
