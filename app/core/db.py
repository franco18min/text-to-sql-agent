"""
Databricks SQL connector wrapper.

Wrapper simple sobre `databricks-sql-connector` que:
- Lee config desde `app.config.settings`
- Expone `execute_query()` que devuelve lista de dicts (columna -> valor)
- Context manager para gestión de conexiones
- `health_check()` para `/health` endpoint

Importante: este módulo NO valida que el SQL sea read-only. Eso se hace
en `app.core.sql_safety.validate_sql` antes de llamar a `execute_query`.
"""
from contextlib import contextmanager
from typing import Iterator

from databricks import sql

from app.config import settings


@contextmanager
def get_connection() -> Iterator["sql.Connection"]:
    """
    Context manager para una conexión al SQL Warehouse.

    Abre con `databricks-sql-connector` y cierra automáticamente al salir
    del bloque `with`. La conexión es TCP+TLS al endpoint del warehouse.
    """
    conn = sql.connect(
        server_hostname=settings.databricks_host,
        http_path=settings.databricks_http_path,
        access_token=settings.databricks_token,
    )
    try:
        yield conn
    finally:
        conn.close()


def execute_query(
    query: str,
    *,
    parameters: dict | None = None,
    fetch: bool = True,
) -> list[dict]:
    """
    Ejecuta un query y devuelve filas como lista de dicts.

    Args:
        query: SQL a ejecutar. Asumimos que ya pasó por `validate_sql()`.
        parameters: dict de named bindings (e.g. `{"catalog": "samples"}`).
        fetch: si True (default) devuelve las filas; si False, ejecuta y
            devuelve lista vacía (útil para EXPLAIN, USE, etc.).

    Returns:
        Lista de dicts con keys = nombres de columna.

    Raises:
        Exception: cualquier error del connector (timeout, auth, syntax).
            El caller decide cómo manejarlo (el agente lo convierte en
            retry con feedback para el LLM).
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, parameters=parameters)
            if not fetch:
                return []
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]


def health_check() -> dict:
    """
    Ping al warehouse con `SELECT 1`. Usado por `/health` y por el
    sanity check al arrancar la API.

    Returns:
        Dict con `databricks_reachable` (bool) y `error` (str) si falló.
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok")
                row = cursor.fetchone()
        return {
            "databricks_reachable": True,
            "warehouse_ok": bool(row and row[0] == 1),
        }
    except Exception as e:
        return {
            "databricks_reachable": False,
            "error": str(e),
        }
