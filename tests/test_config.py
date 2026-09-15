"""Unit tests for Settings defaults (no .env required)."""
from app.config import Settings


def test_default_gemini_model_without_env_or_dotenv(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.gemini_model == "gemini-flash-lite-latest"


def test_gemini_model_env_override_still_allowed(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    settings = Settings(_env_file=None)
    assert settings.gemini_model == "gemini-2.5-flash"
