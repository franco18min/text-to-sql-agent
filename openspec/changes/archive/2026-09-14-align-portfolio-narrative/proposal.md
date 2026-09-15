# Proposal: Align Portfolio Narrative

## Intent

Recruiter docs tell two eval stories and stale product facts. Align all public narrative to **one verifiable story**: current headline **100% (30/30)** from `data/eval/eval_results.json`; **93.3% / Q16 / Q28** as history; EXPLAIN exists; no 0-row retry; notebook exists; version **1.0.0**; demo URL **TBD** (not invented); pytest **recount** at apply; screenshots in `docs/assets/`.

## Scope

### In Scope
- Align `README.md`, `docs/eval-results.md`, `docs/interview-talking-points.md`, light `docs/architecture.md`
- Keep `data/eval/README.md` + JSON as source of truth (merged-run honesty)
- Tree: `notebooks/01_demo.ipynb` exists; optional unused `SCHEMA_RETRIEVAL_PROMPT` footnote
- Capture PNG/GIF into `docs/assets/` (local TPC-H, no fake metrics)
- Version badge 1.0.0; recount tests badge (do not invent count now)

### Out of Scope
- Product features; live Streamlit/HF deploy; inventing a demo URL
- Retry / EXPLAIN / schema HTTP / packaging / CI / CORS code
- Vector Search; implementing unused schema prompt; eval re-run; notebook logic; auth/streaming/BIRD

## Capabilities

### New Capabilities
- `recruiter-eval-narrative`: Current 100% from eval JSON; 93.3% and Q16/Q28 historical; merged-run honesty; talking points/README/eval-results consistent
- `recruiter-agent-facts`: EXPLAIN dry-run yes; exception retry only; no 0-row retry claim; notebook real; version 1.0.0; unused prompt optional
- `recruiter-demo-assets`: Screenshots in `docs/assets/`; local demo steps; public URL TBD never invented; pytest count from real run

### Modified Capabilities
- None (do not change existing `openspec/specs/` code capabilities)

## Approach

**Docs-only + screenshot assets** (exploration Approach 1). Edit markdown to match JSON and code. Restamp `docs/eval-results.md` as historical 93.3%. Recount `pytest` when applying the tests badge. Capture UI locally; prefer few PNGs over a huge GIF.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `README.md` | Modified | 100% eval, 1.0.0, recount tests, notebook tree, assets, no fake URL |
| `docs/eval-results.md` | Modified | History 93.3%; Q16/Q28 fixed; pointer to JSON |
| `docs/interview-talking-points.md` | Modified | Lead 100%; EXPLAIN; drop 0-row retry; demo TBD |
| `docs/architecture.md` | Modified | Light: EXPLAIN + exception retry |
| `docs/assets/` | New | Chat / SQL expander / metadata chips |
| `data/eval/README.md` | Unchanged | Canonical 100% |
| `notebooks/01_demo.ipynb` | Unchanged | Tree mention only |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Recruiter still reads 93.3% as current | High | Restamp eval-results first |
| 0-row retry claim | Med | Match `executor.py` (exceptions only) |
| Invented demo URL | Med | TBD + local `localhost:8501` |
| Overselling full 30 re-run | Med | JSON merged-run note |
| Screenshot needs Databricks+Gemini | Med | Local capture; no mocked scores |
| Test-count drift | Med | Recount at apply |
| Large GIF | Low | Prefer PNGs |

## Rollback Plan

Revert markdown and delete `docs/assets/`. No code/eval/prompt rollback.

## Dependencies

- Local Streamlit + credentials for screenshots
- pytest recount at apply
- Existing JSON (do not regenerate)

## Success Criteria

- [ ] All recruiter surfaces headline 100% from JSON; 93.3%/Q16/Q28 history
- [ ] No 0-row retry; EXPLAIN described accurately
- [ ] Notebook in tree; version 1.0.0; tests badge = recount
- [ ] ≥1 screenshot in `docs/assets/`; no invented public URL
- [ ] Existing main specs unmodified
