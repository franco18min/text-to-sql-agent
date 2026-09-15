"""
Session memory: persistencia de conversación multi-turn.

Dos backends seleccionables por `settings.memory_type`:

1. **`in_memory`** (default para desarrollo):
   - SQLite local en `data/db/sessions.db`
   - No requiere setup
   - Funciona offline
   - Persiste entre runs del mismo proceso

2. **`delta`** (para producción):
   - Delta table en Databricks
   - Persiste en el lakehouse
   - Compartible entre deployments
   - Requiere permisos de escritura en el catalog/schema target

Interfaz pública:
- `save_turn(session_id, role, content, ...)` — guarda un turn
- `get_history(session_id, limit=20)` — recupera los últimos N turns
- `clear_session(session_id)` — borra un session
- `list_sessions(limit=50)` — lista sessions recientes (debug)
"""
import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from app.config import settings

DB_PATH = Path("./data/db/sessions.db")
DEFAULT_LIMIT = 20


@dataclass
class Turn:
    """Un turn de conversación (user o assistant)."""
    session_id: str
    ts: float  # unix timestamp
    role: Literal["user", "assistant"]
    content: str
    sql: str | None = None
    sql_valid: bool | None = None
    execution_error: str | None = None
    retry_count: int = 0
    latency_ms: float = 0.0
    model_used: str | None = None


# ============================================================
# Backend: SQLite (default)
# ============================================================

def _sqlite_init() -> None:
    """Crea la tabla de sessions si no existe."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS turns (
                session_id TEXT NOT NULL,
                ts REAL NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sql TEXT,
                sql_valid INTEGER,
                execution_error TEXT,
                retry_count INTEGER DEFAULT 0,
                latency_ms REAL DEFAULT 0,
                model_used TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_session_ts ON turns (session_id, ts)")


def _sqlite_save(turn: Turn) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO turns
            (session_id, ts, role, content, sql, sql_valid, execution_error, retry_count, latency_ms, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                turn.session_id, turn.ts, turn.role, turn.content,
                turn.sql, int(turn.sql_valid) if turn.sql_valid is not None else None,
                turn.execution_error, turn.retry_count, turn.latency_ms, turn.model_used,
            ),
        )


def _sqlite_get_history(session_id: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT role, content, sql, sql_valid, execution_error, retry_count, latency_ms, model_used
            FROM turns
            WHERE session_id = ?
            ORDER BY ts ASC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        out.append({
            "role": r[0],
            "content": r[1],
            "sql": r[2],
            "sql_valid": bool(r[3]) if r[3] is not None else None,
            "execution_error": r[4],
            "retry_count": r[5],
            "latency_ms": r[6],
            "model_used": r[7],
        })
    return out


def _sqlite_clear_session(session_id: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
        return cur.rowcount


# ============================================================
# Backend: Delta (Databricks)
# ============================================================

def _delta_save(turn: Turn) -> None:
    """
    Guarda en Delta table. Requiere:
    - databricks-sql-connector instalado
    - Catalog/schema configurados con permisos de escritura
    - Tabla `sessions` creada (se crea automáticamente la primera vez)
    """
    from app.core.db import execute_query

    catalog = settings.databricks_catalog
    schema = settings.databricks_schema
    table = f"{catalog}.{schema}.agent_sessions"

    # Crear tabla si no existe (Delta Lake auto-convierte)
    execute_query(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            session_id STRING,
            ts DOUBLE,
            role STRING,
            content STRING,
            sql STRING,
            sql_valid BOOLEAN,
            execution_error STRING,
            retry_count INT,
            latency_ms DOUBLE,
            model_used STRING
        ) USING DELTA
        """,
        fetch=False,
    )

    # Insertar el turn
    execute_query(
        f"""
        INSERT INTO {table} VALUES (
            :session_id, :ts, :role, :content, :sql,
            :sql_valid, :execution_error, :retry_count, :latency_ms, :model_used
        )
        """,
        parameters={
            "session_id": turn.session_id,
            "ts": turn.ts,
            "role": turn.role,
            "content": turn.content,
            "sql": turn.sql,
            "sql_valid": turn.sql_valid,
            "execution_error": turn.execution_error,
            "retry_count": turn.retry_count,
            "latency_ms": turn.latency_ms,
            "model_used": turn.model_used,
        },
        fetch=False,
    )


def _delta_get_history(session_id: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    from app.core.db import execute_query

    catalog = settings.databricks_catalog
    schema = settings.databricks_schema
    table = f"{catalog}.{schema}.agent_sessions"

    rows = execute_query(
        f"""
        SELECT role, content, sql, sql_valid, execution_error, retry_count, latency_ms, model_used
        FROM {table}
        WHERE session_id = :session_id
        ORDER BY ts ASC
        LIMIT :limit
        """,
        parameters={"session_id": session_id, "limit": limit},
    )
    out = []
    for r in rows:
        out.append({
            "role": r["role"],
            "content": r["content"],
            "sql": r["sql"],
            "sql_valid": r["sql_valid"],
            "execution_error": r["execution_error"],
            "retry_count": r["retry_count"],
            "latency_ms": r["latency_ms"],
            "model_used": r["model_used"],
        })
    return out


def _delta_clear_session(session_id: str) -> int:
    from app.core.db import execute_query

    catalog = settings.databricks_catalog
    schema = settings.databricks_schema
    table = f"{catalog}.{schema}.agent_sessions"

    # Para delete rows, el connector no expone rowcount fácil,
    # así que retornamos -1 (unknown). En producción se prefiere
    # soft-delete (UPDATE deleted_at) en vez de DELETE.
    execute_query(
        f"DELETE FROM {table} WHERE session_id = :session_id",
        parameters={"session_id": session_id},
        fetch=False,
    )
    return -1


# ============================================================
# Interfaz pública (selecciona backend según settings)
# ============================================================

def save_turn(
    session_id: str,
    role: Literal["user", "assistant"],
    content: str,
    *,
    sql: str | None = None,
    sql_valid: bool | None = None,
    execution_error: str | None = None,
    retry_count: int = 0,
    latency_ms: float = 0.0,
    model_used: str | None = None,
) -> None:
    """
    Guarda un turn de la conversación.

    Args:
        session_id: identificador de la sesión (sandbox_id del user, etc.)
        role: "user" o "assistant"
        content: texto del mensaje
        sql: SQL generado (solo para assistant)
        sql_valid: pasó el guardrail
        execution_error: error de ejecución (si hubo)
        retry_count: número de intentos
        latency_ms: latencia total del turn
        model_used: nombre del modelo (e.g. "gemini-2.0-flash-exp")
    """
    turn = Turn(
        session_id=session_id,
        ts=time.time(),
        role=role,
        content=content,
        sql=sql,
        sql_valid=sql_valid,
        execution_error=execution_error,
        retry_count=retry_count,
        latency_ms=latency_ms,
        model_used=model_used,
    )
    if settings.memory_type == "delta":
        _delta_save(turn)
    else:
        # in_memory default: usa SQLite
        if not hasattr(save_turn, "_initialized"):
            _sqlite_init()
            save_turn._initialized = True  # type: ignore
        _sqlite_save(turn)


def get_history(session_id: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """
    Recupera los últimos `limit` turns de una sesión en orden cronológico.

    Returns:
        Lista de dicts con keys: role, content, sql, sql_valid, etc.
    """
    if settings.memory_type == "delta":
        return _delta_get_history(session_id, limit)
    if not hasattr(get_history, "_initialized"):
        _sqlite_init()
        get_history._initialized = True  # type: ignore
    return _sqlite_get_history(session_id, limit)


def clear_session(session_id: str) -> int:
    """Borra todos los turns de una sesión. Retorna filas borradas."""
    if settings.memory_type == "delta":
        return _delta_clear_session(session_id)
    if not hasattr(clear_session, "_initialized"):
        _sqlite_init()
        clear_session._initialized = True  # type: ignore
    return _sqlite_clear_session(session_id)
