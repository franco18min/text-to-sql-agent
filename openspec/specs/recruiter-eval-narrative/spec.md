# recruiter-eval-narrative Specification

## Purpose

Recruiter eval claims MUST match `data/eval/eval_results.json`.

## Requirements

### Requirement: Current Headline Matches Eval JSON

`README.md`, `docs/eval-results.md`, and `docs/interview-talking-points.md` MUST headline current accuracy as **100% (30/30)** per JSON. `data/eval/README.md` SHALL stay canonical. Docs SHOULD note merged-run honesty.

#### Scenario: Three surfaces headline 100%

- GIVEN JSON reports 100% (30/30)
- WHEN those three files are read
- THEN each presents 100% (30/30) as current, matching JSON

#### Scenario: Eval-results points at JSON

- GIVEN `docs/eval-results.md`
- WHEN read
- THEN it MUST name the eval JSON or `data/eval/README.md` as source of truth

### Requirement: 93.3 Percent And Q16 Q28 Are History

Those docs MUST treat **93.3%**, **Q16**, and **Q28** as historical. `docs/eval-results.md` MUST restate 93.3% as a prior snapshot.

#### Scenario: History labeled

- GIVEN 93.3%, Q16, or Q28 appear
- WHEN headline sections are scanned
- THEN they MUST be labeled historical, not latest

#### Scenario: Current section excludes 93.3 as latest

- GIVEN current-result sections
- WHEN read without history blocks
- THEN they MUST NOT claim 93.3% as present accuracy
