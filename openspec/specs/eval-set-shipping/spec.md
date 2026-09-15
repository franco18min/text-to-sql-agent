# Eval Set Shipping Specification

## Purpose

`eval_set.json` MUST be trackable in git. Generated `eval_results.json` SHOULD stay ignored.

## Requirements

### Requirement: Track eval set; ignore results

`data/eval/eval_set.json` MUST be trackable in git. `eval_results.json` SHOULD remain ignored and MUST NOT be required as a tracked fixture.

#### Scenario: Clone includes eval set

- GIVEN a fresh clone without extra flags
- WHEN the working tree is listed
- THEN `data/eval/eval_set.json` MUST be present as a tracked file

#### Scenario: Results stay untracked

- GIVEN generated output named `eval_results.json`
- WHEN ignore rules are applied
- THEN that file SHOULD NOT be proposed for commit
