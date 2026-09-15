"""Shared retry_history / retry_count updates for validator and executor."""

from typing import Mapping


def record_retry_failure(state: Mapping, sql: str, error: str) -> dict:
    retry_count = int(state.get("retry_count") or 0) + 1
    history = list(state.get("retry_history") or [])
    history.append({"attempt": retry_count, "sql": sql, "error": error})
    return {"retry_count": retry_count, "retry_history": history}
