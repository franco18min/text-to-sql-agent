"""Contract tests for recruiter-facing docs (eval narrative, agent facts, demo assets)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
EVAL_RESULTS = ROOT / "docs" / "eval-results.md"
TALKING = ROOT / "docs" / "interview-talking-points.md"
ARCHITECTURE = ROOT / "docs" / "architecture.md"
ASSETS = ROOT / "docs" / "assets"
NOTEBOOK = ROOT / "notebooks" / "01_demo.ipynb"

HEADLINE = "100% (30/30)"
HISTORY_MARKERS = (
    "histor",
    "prior",
    "snapshot",
    "previous",
    "anterior",
    "pasado",
    "previ",
    "earlier",
    "before prompt",
)
ZERO_ROW_RETRY = (
    "0 filas",
    "0 rows",
    "zero-row",
    "empty result",
    "empty-result",
    "devuelve 0",
    "returns 0",
    "0-row",
)
LIVE_DEMO_CLAIMS = (
    "streamlit cloud",
    "streamlit community cloud",
    "huggingface spaces",
    "hf spaces",
    "share.streamlit.io",
    "huggingface.co/spaces/",
)
UNUSED_PROMPT_MARKERS = (
    "unused",
    "not used",
    "dead",
    "no se usa",
    "not wired",
    "not active",
    "optional footnote",
)
IMAGE_MD = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
PRODUCT_IMPORT = re.compile(
    r"(?:^|\n)\s*(?:from\s+app\.(?:agent|api)\b|import\s+app\.(?:agent|api)\b)",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _window(text: str, start: int, end: int, radius: int = 240) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)].lower()


def _strip_history_blocks(text: str) -> str:
    parts: list[str] = []
    for block in re.split(r"(?=^#{1,3} )", text, flags=re.MULTILINE):
        heading = block.split("\n", 1)[0].lower()
        if any(m in heading for m in HISTORY_MARKERS):
            continue
        parts.append(block)
    return "\n".join(parts)


def schema_prompt_if_present_is_labeled_unused(text: str) -> None:
    if "SCHEMA_RETRIEVAL_PROMPT" not in text:
        return
    for match in re.finditer(r"SCHEMA_RETRIEVAL_PROMPT", text):
        ctx = _window(text, match.start(), match.end())
        assert any(m in ctx for m in UNUSED_PROMPT_MARKERS), (
            "SCHEMA_RETRIEVAL_PROMPT must be labeled unused when mentioned; "
            f"nearby: {ctx[:180]!r}"
        )


def readme_screenshot_context_does_not_claim_93_3_as_current(text: str) -> None:
    for match in IMAGE_MD.finditer(text):
        alt = match.group(1)
        nearby = (alt + "\n" + text[match.start() : match.end() + 360]).lower()
        if "93.3%" not in nearby and "93.3" not in nearby:
            continue
        if any(m in nearby for m in HISTORY_MARKERS):
            continue
        raise AssertionError(
            "README screenshot caption/alt/nearby must not claim 93.3% as current: "
            f"{nearby[:220]!r}"
        )


def narrative_tests_avoid_product_module_imports(source: str) -> None:
    found = PRODUCT_IMPORT.search(source)
    assert found is None, (
        "narrative tests must not import or mutate app.agent / app.api: "
        f"{found.group(0)!r}"
    )


# --- 1.1 Three surfaces headline 100%; eval-results points at JSON ---


def test_readme_headlines_current_accuracy_100_30_30():
    assert HEADLINE in _read(README)


def test_eval_results_headlines_current_accuracy_100_30_30():
    assert HEADLINE in _read(EVAL_RESULTS)


def test_talking_points_headlines_current_accuracy_100_30_30():
    assert HEADLINE in _read(TALKING)


def test_eval_results_names_json_or_eval_readme_as_source():
    text = _read(EVAL_RESULTS)
    assert "eval_results.json" in text or "data/eval/README.md" in text


# --- 1.2 History labeled; current sections exclude 93.3 as latest ---


def _assert_term_labeled_history(path: Path, term: str) -> None:
    text = _read(path)
    if term not in text:
        return
    for match in re.finditer(re.escape(term), text):
        ctx = _window(text, match.start(), match.end())
        assert any(m in ctx for m in HISTORY_MARKERS), (
            f"{path.name}: {term!r} must be labeled historical/prior/snapshot; "
            f"nearby: {ctx[:180]!r}"
        )


def test_eval_results_93_3_q16_q28_labeled_history():
    _assert_term_labeled_history(EVAL_RESULTS, "93.3%")
    _assert_term_labeled_history(EVAL_RESULTS, "Q16")
    _assert_term_labeled_history(EVAL_RESULTS, "Q28")


def test_readme_93_3_labeled_history_when_present():
    _assert_term_labeled_history(README, "93.3%")
    _assert_term_labeled_history(README, "Q16")
    _assert_term_labeled_history(README, "Q28")


def test_talking_points_93_3_labeled_history_when_present():
    _assert_term_labeled_history(TALKING, "93.3%")
    _assert_term_labeled_history(TALKING, "Q16")
    _assert_term_labeled_history(TALKING, "Q28")


def test_current_eval_sections_do_not_treat_93_3_as_latest():
    for path in (README, EVAL_RESULTS, TALKING):
        current = _strip_history_blocks(_read(path))
        # Remaining 93.3% must still sit next to history markers (inline history).
        for match in re.finditer(r"93\.3%", current):
            ctx = _window(current, match.start(), match.end())
            assert any(m in ctx for m in HISTORY_MARKERS), (
                f"{path.name} current section treats 93.3% as latest: {ctx[:180]!r}"
            )


# --- 1.3 EXPLAIN; zero-row retry absent ---


def test_readme_mentions_explain_dry_run():
    assert "EXPLAIN" in _read(README)


def test_talking_points_mentions_explain_dry_run():
    assert "EXPLAIN" in _read(TALKING)


def test_architecture_mentions_explain_dry_run():
    assert "EXPLAIN" in _read(ARCHITECTURE)


def _assert_no_zero_row_retry(path: Path) -> None:
    text = _read(path)
    lower = text.lower()
    for phrase in ZERO_ROW_RETRY:
        idx = 0
        while True:
            found = lower.find(phrase, idx)
            if found < 0:
                break
            ctx = lower[max(0, found - 160) : found + 160]
            denial = any(
                n in ctx
                for n in ("no por", "not on", "no dispara", "does not", "nunca", "sin retry")
            )
            if denial:
                idx = found + len(phrase)
                continue
            assert "retry" not in ctx and "reintent" not in ctx and "auto-correccion" not in ctx, (
                f"{path.name} claims retry on empty/0-row results: {ctx!r}"
            )
            idx = found + len(phrase)


def _assert_exception_only_retry(path: Path) -> None:
    text = _read(path).lower()
    assert "exception" in text or "error" in text or "falla" in text
    retry_idx = text.find("retry")
    if retry_idx < 0:
        retry_idx = text.find("reintent")
    assert retry_idx >= 0, f"{path.name} must describe retry"
    ctx = text[max(0, retry_idx - 220) : retry_idx + 220]
    assert any(w in ctx for w in ("exception", "error", "falla", "invalid")), (
        f"{path.name} retry must be exception/error-only: {ctx!r}"
    )


def test_readme_retry_is_exception_only_not_zero_row():
    _assert_no_zero_row_retry(README)
    _assert_exception_only_retry(README)


def test_talking_points_retry_is_exception_only_not_zero_row():
    _assert_no_zero_row_retry(TALKING)
    _assert_exception_only_retry(TALKING)


def test_architecture_retry_is_exception_only_not_zero_row():
    _assert_no_zero_row_retry(ARCHITECTURE)
    _assert_exception_only_retry(ARCHITECTURE)


# --- 1.4 Version, notebook, assets, no fabricated live demo ---


def test_readme_displays_version_1_0_0():
    assert "1.0.0" in _read(README)


def test_readme_lists_demo_notebook_and_file_exists():
    text = _read(README)
    assert "notebooks/01_demo.ipynb" in text
    assert NOTEBOOK.is_file()
    assert NOTEBOOK.suffix == ".ipynb"


def test_docs_assets_has_image_linked_from_readme():
    assert ASSETS.is_dir()
    images = [
        p
        for p in ASSETS.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    ]
    assert images, "expected >=1 image under docs/assets/"
    readme = _read(README)
    linked = [img for img in images if f"docs/assets/{img.name}" in readme]
    assert linked, "README must reference at least one docs/assets/* image"


def test_readme_and_talking_points_do_not_claim_live_public_demo():
    for path in (README, TALKING):
        text = _read(path)
        lower = text.lower()
        for claim in LIVE_DEMO_CLAIMS:
            if claim not in lower:
                continue
            for match in re.finditer(re.escape(claim), lower):
                ctx = _window(text, match.start(), match.end(), radius=180)
                live_as_available = (
                    "el link esta" in ctx
                    or "the link is" in ctx
                    or "live demo" in ctx
                    or "demo publica" in ctx
                    or "public demo" in ctx
                    or "deployed at" in ctx
                )
                if live_as_available:
                    raise AssertionError(
                        f"{path.name} treats {claim!r} as a live public demo: {ctx[:200]!r}"
                    )
        if re.search(r"https?://[^\s)]+", text):
            # Public demo may be TBD or omitted; localhost is allowed.
            for url in re.findall(r"https?://[^\s)]+", text):
                if "localhost" in url or "127.0.0.1" in url:
                    continue
                if "streamlit.io/cloud" in url or url.rstrip("/").endswith("huggingface.co/spaces"):
                    # Generic product homepages in a how-to-deploy section are ok
                    # if not presented as this project's live app.
                    continue
                if "share.streamlit.io" in url or "/spaces/" in url:
                    raise AssertionError(f"{path.name} fabricates live demo URL: {url}")


def test_readme_tests_badge_matches_pytest_collect_only():
    text = _read(README)
    badge = re.search(r"tests-(\d+)%20passing", text)
    assert badge, "README tests badge missing"
    published = int(badge.group(1))
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    collected = None
    for line in (proc.stdout + proc.stderr).splitlines():
        m = re.search(r"(\d+) tests? collected", line)
        if m:
            collected = int(m.group(1))
            break
        m = re.search(r"^(\d+) (?:passed|selected)", line.strip())
        if m and collected is None:
            collected = int(m.group(1))
    assert collected is not None, f"could not parse pytest collect-only: {proc.stdout!r} {proc.stderr!r}"
    assert published == collected, f"README badge {published} != pytest collected {collected}"


# --- Unused Schema Prompt Optional; screenshot metrics; docs-only scope ---


def test_schema_prompt_absent_is_vacuous_success():
    schema_prompt_if_present_is_labeled_unused("README without that constant.")


def test_schema_prompt_present_must_be_labeled_unused():
    schema_prompt_if_present_is_labeled_unused(
        "Footnote: `SCHEMA_RETRIEVAL_PROMPT` is unused on the tpch path."
    )


def test_schema_prompt_present_without_unused_label_fails():
    unlabeled = "We use SCHEMA_RETRIEVAL_PROMPT for live Vector Search."
    try:
        schema_prompt_if_present_is_labeled_unused(unlabeled)
    except AssertionError:
        return
    raise AssertionError("expected unlabeled SCHEMA_RETRIEVAL_PROMPT to fail")


def test_recruiter_docs_schema_prompt_honesty_vacuous_or_labeled():
    for path in (README, EVAL_RESULTS, TALKING, ARCHITECTURE):
        schema_prompt_if_present_is_labeled_unused(_read(path))


def test_screenshot_caption_claiming_93_3_as_current_fails():
    dishonest = (
        "![UI](docs/assets/demo.png)\n\n"
        "Caption: current eval accuracy 93.3% on this screenshot.\n"
    )
    try:
        readme_screenshot_context_does_not_claim_93_3_as_current(dishonest)
    except AssertionError:
        return
    raise AssertionError("expected 93.3% as current next to screenshot to fail")


def test_screenshot_caption_without_93_3_as_current_passes():
    honest = "![UI local TPC-H](docs/assets/streamlit-ui-chrome.png)\n\nLocal chrome, no eval %.\n"
    readme_screenshot_context_does_not_claim_93_3_as_current(honest)


def test_readme_screenshot_context_does_not_claim_93_3_as_current():
    readme_screenshot_context_does_not_claim_93_3_as_current(_read(README))


def test_importing_app_agent_in_narrative_tests_is_detected():
    dirty = "from app.agent import graph\n"
    try:
        narrative_tests_avoid_product_module_imports(dirty)
    except AssertionError:
        return
    raise AssertionError("expected app.agent import to fail docs-only check")


def test_this_narrative_file_does_not_import_or_mutate_app_agent_or_app_api():
    narrative_tests_avoid_product_module_imports(Path(__file__).read_text(encoding="utf-8"))
