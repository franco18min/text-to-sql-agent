# Design: Align Portfolio Narrative

## Technical Approach

Docs-only + screenshot assets (proposal Approach 1; specs `recruiter-eval-narrative`, `recruiter-agent-facts`, `recruiter-demo-assets`). No LangGraph, FastAPI, eval runner, or prompt changes. Recruiter markdown must match `data/eval/eval_results.json` (current **100% 30/30**, merged-run note) and shipped code: `sql_validator.py` EXPLAIN dry-run; `executor.py` exception-only retry (empty results are success). Leave `data/eval/README.md` and JSON as SoT. Recount pytest at apply; do not invent a public demo URL.

## Architecture Decisions

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Edit markdown + commit local PNGs vs live deploy + wire unused prompt | Deploy/code out of scope; unused `SCHEMA_RETRIEVAL_PROMPT` is dead | **Docs + assets only** |
| Headline JSON 100% vs leave `docs/eval-results.md` as 93.3% current | Dual story is the bug | **100% current**; restamp 93.3% / Q16 / Q28 as history |
| Keep merged-run honesty vs imply full 30 re-run | JSON `note` is merger | **Cite merge**; do not regenerate eval |
| Badge tests 102 now vs recount at apply | Count drifted after packaging tests | **Recount at apply** (placeholder until then) |
| Version badge 1.0.0 vs omit | Code already 1.0.0 (`pyproject.toml`, `app/__init__.py`) | **Show 1.0.0** in README |
| TBD / localhost vs Streamlit Cloud / HF as live | No owned public URL | **TBD**; keep `localhost:8501` |
| Few PNGs vs large GIF | Size / fake metrics | **≥1 PNG** under `docs/assets/`; no mocked scores |
| Tree `notebooks/01_demo.ipynb` vs “placeholder” | File exists | **List real notebook**; do not edit it |
| Optional unused-prompt footnote vs imply Vector Search | Prompt unused; VS not on tpch | **MAY footnote unused**; never claim active VS |

## Data Flow

```mermaid
sequenceDiagram
  participant Apply as Docs apply
  participant JSON as eval_results.json
  participant Code as validator/executor
  participant Pytest as pytest collect
  participant UI as Streamlit local
  participant Docs as README/eval/talking/arch
  Apply->>JSON: current 100% + merge note
  Apply->>Code: EXPLAIN; exception retry only
  Apply->>Pytest: recount for tests badge
  Apply->>UI: capture TPC-H screenshots
  Apply->>Docs: one story; history labeled; assets linked
```

```
eval JSON + eval README (unchanged SoT)
        │
        ▼
README + eval-results + talking-points  ── current 100%; 93.3% history
        │
executor.py / sql_validator.py (read-only) ── EXPLAIN; no 0-row retry
        │
docs/architecture.md (light) + docs/assets/*.png
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `README.md` | Modify | 100% from JSON; 1.0.0; pytest recount; notebook tree; assets; drop 93% as current in honesty list; EXPLAIN; exception retry; demo TBD not Cloud/HF as live |
| `docs/eval-results.md` | Modify | Current 100%; 93.3%/Q16/Q28 history; pointer to JSON/`data/eval/README.md` |
| `docs/interview-talking-points.md` | Modify | Lead 100%; EXPLAIN; drop 0-row retry; demo TBD + localhost |
| `docs/architecture.md` | Modify | Light: EXPLAIN dry-run; retry on executor exceptions only |
| `docs/assets/` | Create | ≥1 PNG (chat / SQL expander / chips); no fake eval % |
| `data/eval/README.md` | Unchanged | Canonical 100% |
| `data/eval/eval_results.json` | Unchanged | Do not re-run |
| `notebooks/01_demo.ipynb` | Unchanged | Tree mention only |
| `openspec/specs/` | Unchanged | No product capability merge |

## Interfaces / Contracts

Copy constraints (no new APIs):

- Current accuracy string: `100% (30/30)` matching JSON.
- History labels required if 93.3%, Q16, or Q28 appear.
- Retry wording: validator/EXPLAIN or executor **exceptions**; never empty result sets.
- Public demo: `TBD` or omitted; `http://localhost:8501` allowed.
- Tests badge: integer from `pytest --collect-only` at apply.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | N/A (no product code) | Skip |
| Integration | N/A | Skip |
| E2E | N/A | Skip |
| Apply verify | Spec scenarios | Grep/read: 100% headline, history labels, EXPLAIN, no 0-row, 1.0.0, notebook path exists, ≥1 `docs/assets/` file linked, TBD URL, pytest count equals badge |

`strict_tdd` does not apply: no failing tests before docs. Optional: packaging tests already assert some README strings — if they pin “102”, update tests only if they fail after recount (prefer docs-only; adjust tests only if required for green CI).

## Migration / Rollout

No migration. Ship as one docs PR. Rollback: revert markdown, delete `docs/assets/`.

## Open Questions

- [ ] Exact pytest collected count (fill at apply).
- [ ] Whether CI packaging tests pin “102 tests” (check at apply; change tests only if they fail).
