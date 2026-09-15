# Windows Pytest Docs Specification

## Purpose

README MUST document pytest on Windows without Make.

## Requirements

### Requirement: Windows pytest without Make

The README MUST document running pytest on Windows without Make, including `python -m pytest tests/ -v` and `run_tests.py`. Documented Docker build MUST be a real build command.

#### Scenario: Windows pytest without Make

- GIVEN a Windows clone without Make
- WHEN the reader follows README test instructions
- THEN they MUST be able to run pytest without Make
- AND `python -m pytest tests/ -v` and `run_tests.py` MUST both be documented

#### Scenario: Docker build docs are honest

- GIVEN README Docker instructions
- WHEN a reader runs the documented build command
- THEN that command MUST build an image (not a no-op target)
