# Tasks: Align Portfolio Narrative

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 120–250 text (+ small PNGs) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Docs + assets + grep tests | PR 1 | Markdown/tests; PNGs not line-budget |

## Phase 1: RED — narrative grep tests

- [x] 1.1 Add `tests/test_docs_narrative.py` reading `README.md`, `docs/eval-results.md`, `docs/interview-talking-points.md`, `docs/architecture.md`. Assert those three eval surfaces contain `100% (30/30)` as current; eval-results names `eval_results.json` or `data/eval/README.md` (recruiter-eval-narrative: Three surfaces headline 100%; Eval-results points at JSON). Fail until docs land.
- [x] 1.2 Same file: if `93.3%` / `Q16` / `Q28` appear, require history/prior/snapshot language; current sections MUST NOT treat 93.3% as latest (History labeled; Current section excludes 93.3 as latest).
- [x] 1.3 Same file: README, talking-points, architecture mention `EXPLAIN`; retry text MUST NOT claim 0-row/empty-result retry (EXPLAIN mentioned; Zero-row retry absent).
- [x] 1.4 Same file: README has `1.0.0` and `notebooks/01_demo.ipynb`; `Path` exists; ≥1 `docs/assets/*` image and README references it; README+talking-points MUST NOT treat Streamlit Cloud/HF as a live public demo (Version text; Notebook path and file; Asset on disk and in README; No fabricated live link). Run `pytest tests/test_docs_narrative.py -v` — RED.

## Phase 2: GREEN — eval and agent docs

- [x] 2.1 `docs/eval-results.md`: current 100% (30/30); 93.3%/Q16/Q28 historical; pointer to JSON/`data/eval/README.md`. Do not edit JSON or `data/eval/README.md`.
- [x] 2.2 `docs/interview-talking-points.md`: lead 100%; EXPLAIN; exception-only retry; drop 0-row; demo TBD + `localhost:8501`.
- [x] 2.3 `docs/architecture.md` (light): EXPLAIN dry-run; retry on executor exceptions only.
- [x] 2.4 `README.md`: 100% current (drop 93% as current in honesty list); version 1.0.0; notebook tree; EXPLAIN; exception retry; public URL TBD; placeholder tests badge until recount. Optional unused-prompt footnote only if labeled unused (never Vector Search).

## Phase 3: GREEN — assets

- [x] 3.1 Create `docs/assets/` with ≥1 local TPC-H PNG (chat / SQL expander / chips). No mocked eval %. Link from README. Pass 1.4 asset asserts.

## Phase 4: GREEN — recount and CI pin

- [x] 4.1 Run `pytest --collect-only`; set README tests badge to that integer (Badge matches pytest). Do not invent count earlier.
- [x] 4.2 If packaging tests pin `102`, update only those asserts so CI stays green. No product code. Pass `pytest tests/test_docs_narrative.py -v`.

## Phase 5: Verify

- [x] 5.1 `pytest tests/ -v`. Confirm `openspec/specs/` and notebook/JSON untouched. Rollback: revert markdown, delete `docs/assets/`.

## Phase 6: Verify follow-up — covering tests for UNTESTED scenarios

- [x] 6.1 Add covering tests in `tests/test_docs_narrative.py` for Unused Schema Prompt Optional (vacuous if absent), no mocked 93.3% as current near screenshot, and docs-only scope (no `app.agent` / `app.api` imports). Recount README tests badge. No product-module mutation.
