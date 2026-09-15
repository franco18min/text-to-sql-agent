# recruiter-demo-assets Specification

## Purpose

Demo proof MUST use local assets, honest URLs, and pytest recount.

## Requirements

### Requirement: Screenshot Assets Referenced

≥1 image MUST exist under `docs/assets/`. README MUST reference ≥1 such file. Images SHALL show local TPC-H UI, not fake scores.

#### Scenario: Asset on disk and in README

- GIVEN `docs/assets/` after this change
- WHEN images and README links are inspected
- THEN ≥1 image exists AND README MUST reference at least one path

#### Scenario: No mocked eval metrics in assets

- GIVEN `docs/assets/` files
- WHEN used as recruiter proof
- THEN they MUST NOT invent eval % contradicting eval JSON

### Requirement: Public Demo URL Not Invented

Docs MUST NOT publish a fabricated live public demo URL. They MUST use **TBD** or omit it. They MAY document `localhost:8501`.

#### Scenario: No fabricated live link

- GIVEN README and talking-points
- WHEN scanned for public demo http(s) links
- THEN they MUST NOT present an unowned live demo as available
- AND a missing public URL MUST be TBD or omitted

### Requirement: Tests Count From Real Pytest

README test count MUST equal pytest collection at apply.

#### Scenario: Badge matches pytest

- GIVEN README states a test count
- WHEN pytest is collected
- THEN the published count MUST match collected tests

### Requirement: Docs-Only Scope

Apply SHALL be markdown, assets, and pytest recount only.

#### Scenario: No product code obligation

- GIVEN this spec
- WHEN apply is planned
- THEN product code MUST NOT be required to change
