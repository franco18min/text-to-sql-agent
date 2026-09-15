"""Contract tests for clone/CI/Docker packaging files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_copies_env_example():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY env.example .env" in text
    assert "COPY .env.example .env" not in text


def test_env_example_header_names_source_file():
    text = (ROOT / "env.example").read_text(encoding="utf-8")
    assert "cp env.example .env" in text
    assert "cp .env.example .env" not in text


def test_gitignore_tracks_eval_set_and_ignores_results():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/eval/*.json" in text
    assert "!data/eval/eval_set.json" in text


def test_ci_uses_editable_dev_install():
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert 'pip install -e ".[dev]"' in text


def test_runtime_pins_do_not_include_unpublished_langchain_google_genai_1_0_0():
    """PyPI never published 1.0.0 (0.0.11 then 1.0.1); CI pip install -e .[dev] fails."""
    for rel in ("pyproject.toml", "requirements.txt"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert "langchain-google-genai==1.0.0" not in text, (
            f"{rel} pins langchain-google-genai==1.0.0 which is not on PyPI"
        )


def test_httpx_is_not_pinned_to_0_26():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "httpx==0.26.0" not in pyproject
    assert "httpx==0.26.0" not in req


def test_vectorsearch_sdks_are_optional_extra_not_runtime():
    """databricks-vectorsearch 0.75 needs protobuf 5; streamlit 1.31 / Gemini 0.3.2 need protobuf<5."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    main, extras = text.split("[project.optional-dependencies]", 1)
    assert "databricks-vectorsearch" not in main
    assert "databricks-ai-search" not in main
    assert "databricks-vectorsearch" in extras
    assert "databricks-ai-search" in extras
    assert 'vectorsearch' in extras


def test_run_tests_wrapper_has_no_timeout_flag():
    text = (ROOT / "run_tests.py").read_text(encoding="utf-8")
    assert "--timeout=15" not in text
    assert '"-m", "pytest", "tests/"' in text or "pytest" in text


def test_makefile_has_docker_build_target():
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "docker-build" in text
    assert "docker build -t text-to-sql-agent ." in text


def test_readme_documents_windows_pytest_and_honest_docker_build():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "python -m pytest tests/ -v" in text
    assert "run_tests.py" in text
    assert "docker build -t text-to-sql-agent ." in text
    assert 'pip install -e ".[dev]"' in text


def test_pyproject_version_is_1_0_0():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.0.0"' in text
