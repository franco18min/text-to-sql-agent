# CI Editable Install Specification

## Purpose

CI MUST install the package with developer extras so agent tests can import langgraph, matching clone docs.

## Requirements

### Requirement: Editable install with dev extras

The CI workflow MUST install the project in editable mode with the `dev` extra before pytest. After that install, agent tests MUST be able to import `langgraph`.

#### Scenario: Agent tests import langgraph

- GIVEN a CI job that runs the project test suite
- WHEN the job installs the package before pytest
- THEN the install MUST be editable with the `dev` extra
- AND `tests/test_agent.py` MUST be able to import `langgraph`

#### Scenario: Clone docs match CI

- GIVEN README install instructions for local tests
- WHEN a contributor compares them to CI
- THEN both MUST use editable install with the `dev` extra
