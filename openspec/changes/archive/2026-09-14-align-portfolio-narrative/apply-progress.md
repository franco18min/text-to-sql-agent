# Apply progress: align-portfolio-narrative

**Mode**: Strict TDD  
**Batch**: verify-follow-up covering tests (merged with prior apply)  
**Pytest collected**: 182  
**Product code**: unchanged (`app.agent` / `app.api` not imported or mutated)

## Completed tasks

- [x] 1.1–1.4 RED `tests/test_docs_narrative.py`
- [x] 2.1–2.4 GREEN recruiter markdown
- [x] 3.1 `docs/assets/streamlit-ui-chrome.png` linked from README
- [x] 4.1 Badge recounted; 4.2 packaging did not pin 102
- [x] 5.1 prior `pytest tests/ -v` → 173 passed
- [x] 6.1 Covering tests for three UNTESTED verify scenarios; badge `182`; suite 182 passed

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_docs_narrative.py` | Unit (docs grep) | N/A (new) | ✅ Written (headline + JSON pointer failed) | ✅ Passed after eval/README/talking 100% (30/30) | ✅ 3 surfaces + pointer | ➖ None needed |
| 1.2 | same | Unit | N/A (new) | ✅ Written (93.3/Q16/Q28 unlabeled) | ✅ Passed after history sections | ✅ history labels + current strip | ➖ None needed |
| 1.3 | same | Unit | N/A (new) | ✅ Written (no EXPLAIN; 0-row retry) | ✅ Passed after EXPLAIN + exception retry | ✅ 3 files; denial vs claim on 0 filas | ✅ Helper allows explicit denials |
| 1.4 | same | Unit | N/A (new) | ✅ Written (no 1.0.0, notebook placeholder, no asset, live Cloud/HF claim, badge 102) | ✅ Passed | ✅ version + notebook Path + PNG link + no live URL + badge==collect | ➖ None needed |
| 2.1–2.4 | same | Unit | README/docs existing; packaging green | covered by 1.x | ✅ Docs green | same | honesty list restamped as history |
| 3.1 | `test_docs_assets_has_image_linked_from_readme` | Unit | N/A (new dir) | ✅ Written (no assets dir) | ✅ PNG + README link | ➖ Single (asset presence) | ➖ Chrome PNG (Streamlit started; browser MCP had no tab — shipped local chrome, no eval %) |
| 4.1 | `test_readme_tests_badge_matches_pytest_collect_only` | Unit | collect-only 173 then 182 | ✅ 102≠173; badge lag 173≠182 | ✅ badge matches collect | ➖ Single (one integer) | ➖ None |
| 4.2 | packaging | Unit | no `102` pin | ➖ N/A | ➖ no test change | ➖ skipped: no pin | ➖ |
| 5.1 | `pytest tests/` | Unit | 173/173 then 182/182 | N/A | ✅ 182 passed | N/A | N/A |
| 6.1 schema prompt | `test_schema_prompt_*` | Unit | ✅ 19/19 narrative | ✅ NameError (helper missing) | ✅ helpers + recruiter docs vacuous | ✅ absent / labeled / unlabeled fail / real docs | ➖ helpers colocated |
| 6.1 screenshot 93.3 | `test_*screenshot*` | Unit | same | ✅ NameError | ✅ caption/alt/nearby check | ✅ dishonest fail + honest pass + real README | ➖ None needed |
| 6.1 docs-only | `test_*product_module*` | Unit | same | ✅ NameError | ✅ import-line regex | ✅ dirty `from app.agent` fail + this file pass | ➖ AST-like line scan not string literals |

### Test Summary

- **Total tests written**: 28 in `test_docs_narrative.py` (prior 19 + 9 covering)
- **Total tests passing**: 182 (full suite)
- **Layers used**: Unit (28 narrative), Integration (0), E2E (0)
- **Approval tests**: None — no product refactor
- **Pure functions created**: 3 (`schema_prompt_if_present_is_labeled_unused`, `readme_screenshot_context_does_not_claim_93_3_as_current`, `narrative_tests_avoid_product_module_imports`)

## Deviations

- Design said `strict_tdd` does not apply; orchestrator required Strict TDD — followed tests-first grep contracts.
- Streamlit ran on `:8501`; Cursor browser had no tab. PNG is real UI chrome (title, SQL expander, chips), not a live TPC-H query capture. No fabricated eval %.
- Public demo: TBD / omitted; no invented URL.
- Verify follow-up: recruiter prose unchanged except tests badge 173→182 required by existing badge contract.

## Status

12/12 tasks complete (11 prior + 6.1). Ready for sdd-verify.
