# Unified Version Specification

## Purpose

Published API and package version MUST be `1.0.0` on `GET /` and health.

## Requirements

### Requirement: Version 1.0.0 everywhere

Package metadata, application version, `GET /`, and health MUST all report `1.0.0`. Surfaces MUST NOT disagree.

#### Scenario: Root and health report 1.0.0

- GIVEN a running API
- WHEN a client calls `GET /` and the health endpoint
- THEN both responses MUST include version `1.0.0`

#### Scenario: Package matches API

- GIVEN installed package metadata
- WHEN version is compared with API version
- THEN both MUST be `1.0.0`
