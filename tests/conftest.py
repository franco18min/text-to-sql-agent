"""Shared pytest fixtures. Isolated SQLite so CI has a `turns` table."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolated_sqlite_sessions(tmp_path, monkeypatch):
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr("app.core.memory.DB_PATH", db_path)
    from app.core.memory import _sqlite_init

    _sqlite_init()
