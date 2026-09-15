## Exploration: align-portfolio-narrative

### Current State

Recruiter-facing docs tell **two eval stories** and several **stale facts**. Product code (retry, EXPLAIN, packaging, schema HTTP) is already done; this change is narrative + assets only.

**Eval (verified):**

| Surface | Headline accuracy | Q16/Q28 |
|---|---|---|
| `README.md` badges + TL;DR + results table | **100% (30/30)** | History 83% → 93% → 100% |
| `data/eval/README.md` + `data/eval/eval_results.json` (`execution_accuracy_pct`: 100.0) | **100% (30/30)** | Historical row: 93.3% when they failed; then 3 prompt rules |
| `docs/eval-results.md` | **93.3% (28/30)** | Still listed as **current** failures with “Fix sugerido (Fase 9)” |
| `docs/interview-talking-points.md` | Leads with **93.3%**, then “~100% ambos” | Quality section still says 83% → 93% as the last prompt win |

Canonical story for this change: **100% is the current verified headline** (JSON + eval README). **93.3% / Q16 / Q28 is history**, not the live scorecard. Do not re-run eval or change prompts.

**Retry / EXPLAIN (verified vs talking points):**

- `sql_validator.py` **does** EXPLAIN dry-run after LIMIT persist; EXPLAIN failure writes `retry_history` (change 1).
- `executor.py` retries only on **exception**, not on **0 rows**. Empty successful result is success.
- Talking points still claim retry when the query “devuelve 0 filas” — **false**. Keep EXPLAIN; drop 0-row retry from the script.

**Unused prompt (verified):** `SCHEMA_RETRIEVAL_PROMPT` is defined only in `app/agent/prompts.py` (no other references). Schema path is SHOW TABLES + DESCRIBE, not this LLM. Optional honest footnote; **do not implement Vector Search**.

**Notebook / tree:** `notebooks/01_demo.ipynb` exists (schema-surface change). README tree still says `notebooks/` is a placeholder/roadmap. Tree also omits `GET /schema` (implemented in `app/main.py`).

**Version:** Package/API is **1.0.0** (`pyproject.toml`, `app/__init__.py`, `/` and `/health`). README has **no version badge** (only LangGraph 0.2, Python 3.11+, tests-102). Recruiter story should say **1.0.0** without implying other product versions.

**Tests badge:** README still says **102 tests** and a 69+18+15 split. Post-packaging/schema files exist (`test_packaging.py`, `test_config.py`, `test_demo_notebook.py`, expanded API). Recount at apply time; do not invent a number here.

**Screenshots / demo URL:** **No png/gif** in the repo. Interview cheatsheet points to a public Streamlit/HF link “en el README”; README only documents local `localhost:8501` and generic deploy how-tos. **Demo URL TBD — do not invent a live URL.** Local demo steps stay valid.

**Out of scope (confirmed):** auth, streaming, BIRD, live Streamlit Cloud deploy, retry/schema/packaging code.

### Affected Areas

- `README.md` — badges (eval already 100%; add 1.0.0; fix test count if recounting), tree (`notebooks/01_demo.ipynb`), embed or link screenshots, no fake demo URL, optional unused-prompt footnote
- `docs/eval-results.md` — restamp as **historical 93.3% run**; point current score to `data/eval/README.md` / JSON; Q16/Q28 as **fixed** (prompt rules), not open failures
- `data/eval/README.md` — already 100%; keep as source of truth; ensure README/eval-results do not contradict it
- `docs/interview-talking-points.md` — lead 100%; history 93.3%; EXPLAIN yes; **no 0-row retry**; demo URL TBD / local only
- `docs/architecture.md` — light pass: EXPLAIN + exception retry; no 0-row claim if added later; unused prompt optional
- New `docs/assets/` (or `docs/screenshots/`) — PNG/GIF of Streamlit chat, SQL expander, metadata chips (captured locally)
- `notebooks/01_demo.ipynb` — mention in tree only; do not change notebook logic
- `app/agent/prompts.py` — mention unused `SCHEMA_RETRIEVAL_PROMPT` only; no code
- Not in scope: `app/agent/nodes/*`, packaging, CI, CORS, Vector Search

### Approaches

1. **Docs-only + screenshot assets** — One recruiter story: 100% current / 93.3% history; EXPLAIN dry-run; no 0-row retry; notebook exists; version 1.0.0; local demo + TBD public URL; commit PNG/GIF; optional unused-prompt line.
   - Pros: Verifiable against JSON and code; recruiter can see UI without a live deploy; no product risk; fits “do not add features”
   - Cons: Screenshots need a local run (credentials); GIFs can be large; test-count badge needs a real pytest count at apply
   - Effort: Low

2. **Docs text-only (no images)** — Same number/fact alignment without binaries.
   - Pros: Smallest diff; no capture session
   - Cons: Recruiter first impression is still a wall of markdown; talking points already say “video/UI not code”
   - Effort: Low

3. **Docs + live deploy URL + VS schema prompt** — Ship Streamlit Cloud and wire `SCHEMA_RETRIEVAL_PROMPT`.
   - Pros: Clickable demo
   - Cons: Out of scope; invents URL or requires deploy; implements VS — forbidden
   - Effort: High

### Recommendation

Use **Approach 1**. Single narrative:

1. **Now:** 30/30 execution accuracy and 100% execution success (`eval_results.json` + `data/eval/README.md`).
2. **Then:** 83.3% (bad GTs) → 93.3% (Q16 year filter, Q28 count-of-X-with-Y) → 100% (three prompt rules). Move Q16/Q28 in `docs/eval-results.md` to a **historical** section.
3. **Loop:** EXPLAIN dry-run + retry on validation/execution **errors**; **not** empty result sets.
4. **Surfaces:** `notebooks/01_demo.ipynb` is real; version **1.0.0**; demo is **local / URL TBD**; optional “unused `SCHEMA_RETRIEVAL_PROMPT`” honesty.

Do not add product features. Recount pytest for the tests badge during apply.

### Risks

- Recruiter reads `docs/eval-results.md` first and still believes 93.3% / open Q16–Q28 if that file is not restamped.
- Claiming 0-row retry after change 1 is a **lie** a technical interviewer can disprove in `executor.py`.
- Inventing a Streamlit/HF URL fails the first click.
- Screenshots of live TPC-H answers need Databricks + Gemini; capture locally, do not mock fake metrics in images.
- `eval_results.json` note admits a **merged** run (12 questions on new prompt, 18 carried from old). Headline 100% is what the JSON reports; do not oversell “full 30 re-run on new prompt” unless that is re-verified. Honesty: merged artifact, known failures re-run and fixed.
- Test-count drift if badge stays 102 after packaging/schema tests.
- Binary size if GIF is huge; prefer a few PNGs + one short GIF.

### Ready for Proposal

Yes. Orchestrator should run **sdd-propose** for `align-portfolio-narrative`: docs + screenshot assets only; canonical 100% with 93.3% as history; EXPLAIN yes / 0-row retry no; notebook tree fix; 1.0.0; demo URL TBD; unused prompt optional. No retry/schema/packaging/auth/streaming/BIRD/VS work.
