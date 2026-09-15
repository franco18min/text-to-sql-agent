# Gemini Default Model Specification

## Purpose

Default Gemini model MUST be `gemini-flash-lite-latest` without requiring a `.env` file.

## Requirements

### Requirement: Default without .env

When `GEMINI_MODEL` is unset, configuration MUST use `gemini-flash-lite-latest`. A `.env` file MUST NOT be required for that default. The template default MUST match.

#### Scenario: Unset GEMINI_MODEL without .env

- GIVEN no `GEMINI_MODEL` and no `.env`
- WHEN configuration is loaded
- THEN the Gemini model MUST be `gemini-flash-lite-latest`

#### Scenario: Env override still allowed

- GIVEN `GEMINI_MODEL` is set to another value
- WHEN configuration is loaded
- THEN that value MUST be used instead of the default
