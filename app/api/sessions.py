"""
Sessions router — gestión del historial de conversaciones.

Endpoints:
- POST   /sessions                       -> crea una session vacía (con id nuevo)
- GET    /sessions                       -> lista sessions recientes
- GET    /sessions/{session_id}          -> historial completo de una session
- DELETE /sessions/{session_id}          -> borra una session

Nota: el agente también guarda automáticamente cada turn (assistant + user) en
session memory durante run_agent(). Acá exponemos esos turnos al frontend.
"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query, status

from app.core.memory import clear_session, get_history
from app.models.response import (
    HistoryTurn,
    SessionActionResponse,
    SessionHistoryResponse,
    SessionsListResponse,
    SessionSummary,
)


router = APIRouter(prefix="/sessions", tags=["sessions"])


# ------------------------------------------------------------
# Helpers — depende del backend (SQLite / Delta) en memory.py
# ------------------------------------------------------------

def _list_recent_sessions_sqlite(limit: int) -> list[SessionSummary]:
    """Lee las sessions más recientes desde SQLite. Solo si el backend es in_memory."""
    import sqlite3
    from app.core.memory import DB_PATH

    if not DB_PATH.exists():
        return []

    with sqlite3.connect(DB_PATH) as conn:
        agg_rows = conn.execute(
            """
            SELECT session_id, COUNT(*), MIN(ts), MAX(ts)
            FROM turns
            GROUP BY session_id
            ORDER BY MAX(ts) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        out: list[SessionSummary] = []
        for sid, turn_count, first_ts, last_ts in agg_rows:
            last_q = conn.execute(
                """
                SELECT content FROM turns
                WHERE session_id = ? AND role = 'user'
                ORDER BY ts DESC LIMIT 1
                """,
                (sid,),
            ).fetchone()
            out.append(SessionSummary(
                session_id=sid,
                turn_count=int(turn_count),
                first_ts=float(first_ts),
                last_ts=float(last_ts),
                last_question=(last_q[0][:120] if last_q else None),
            ))
        return out


# ------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------

@router.post("", response_model=SessionActionResponse, status_code=status.HTTP_201_CREATED)
async def create_session():
    """Crea un session_id nuevo. Útil si el cliente quiere iniciar tracking antes de la primera pregunta."""
    return SessionActionResponse(
        session_id=f"sess_{uuid.uuid4().hex[:12]}",
        action="created",
    )


@router.get("", response_model=SessionsListResponse)
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=200, description="Cantidad máxima de sessions a devolver"),
):
    """Lista las sessions más recientes (ordenadas por última actividad)."""
    from app.config import settings

    if settings.memory_type == "delta":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Listado de sessions en backend Delta todavía no implementado.",
        )
    sessions = _list_recent_sessions_sqlite(limit)
    return SessionsListResponse(sessions=sessions, total=len(sessions))


@router.get("/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=500),
):
    """Devuelve el historial completo (turns user+assistant) de una session."""
    history = get_history(session_id, limit=limit)
    return SessionHistoryResponse(
        session_id=session_id,
        turn_count=len(history),
        history=[HistoryTurn(**h) for h in history],
    )


@router.delete("/{session_id}", response_model=SessionActionResponse)
async def delete_session(session_id: str):
    """Borra todos los turns de una session."""
    affected = clear_session(session_id)
    return SessionActionResponse(
        session_id=session_id,
        action="cleared",
        affected_rows=int(affected) if affected is not None else 0,
    )
