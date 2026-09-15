"""Shared LIMIT cap for validator persist and executor recap."""

from app.core.sql_safety import add_limit_if_missing


def cap_sql_query(sql: str, max_rows: int) -> str:
    return add_limit_if_missing(sql, max_rows=max_rows)
