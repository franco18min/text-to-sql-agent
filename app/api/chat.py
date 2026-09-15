"""
POST /query — endpoint principal del agente Text-to-SQL.

Delega toda la lógica al grafo LangGraph (`app.agent.graph.run_agent`).
Solo se encarga de:
- Mapear QueryRequest → args de run_agent
- Truncar results a max_rows si el caller lo pidió
- Derivar campos derivados (rows_returned, validation_status)
- Devolver el AgentResponse con todos los metadatos
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.models.query import QueryRequest
from app.models.response import AgentResponse


router = APIRouter(tags=["chat"])


# Helpers ---------------------------------------------------------------------

def _truncate_results(results: list[dict], max_rows: int | None) -> list[dict]:
    """Trunca results a max_rows. None = sin límite (pero cap por settings)."""
    cap = max_rows if max_rows is not None else settings.max_result_rows
    return results[:cap]


def _derive_validation_status(
    sql_query: str | None,
    error: str | None,
    intent: str | None,
) -> str:
    """Deriva un status legible del estado de validación del SQL."""
    if intent in {"chitchat", "clarification", "give_up"}:
        return "not_applicable"
    if not sql_query:
        return "skipped"
    if error and ("validation" in error.lower() or "forbidden" in error.lower()):
        return "invalid"
    return "valid"


def _run_agent_or_503(question: str, session_id: str) -> dict[str, Any]:
    """Invoca run_agent y captura errores fatales como 503."""
    try:
        from app.agent.graph import run_agent  # import lazy para no romper /health
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agente no disponible (import error): {e}",
        )
    try:
        return run_agent(question=question, session_id=session_id)
    except Exception as e:
        # Si el agente explotó a mitad de camino, devolvemos 500 con detalle
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agente falló: {type(e).__name__}: {e}",
        )


# Endpoint --------------------------------------------------------------------

@router.post("/query", response_model=AgentResponse)
def post_query(request: QueryRequest):
    """
    Procesa una pregunta en lenguaje natural y devuelve:
    - answer (lenguaje natural)
    - sql_query (si include_sql=true)
    - results (filas, truncadas a max_rows)
    - metadata: intent, schema_source, validation_status, retry_count, latency_ms

    Sync on purpose: `run_agent` is blocking (LLM + Databricks) and must
    run in the FastAPI threadpool instead of the event loop.

    Si el cliente no manda session_id, se genera uno nuevo (UUID4).
    """
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:12]}"

    t0 = time.perf_counter()
    raw = _run_agent_or_503(request.question, session_id)
    wall_ms = (time.perf_counter() - t0) * 1000.0

    # Latencia reportada: la del agente (más precisa) + overhead del wrapper
    agent_latency_ms = float(raw.get("latency_ms", 0.0)) or wall_ms

    # Truncar results
    results = raw.get("results") or []
    if not request.include_results:
        results = []
    elif request.max_rows is not None:
        results = _truncate_results(results, request.max_rows)

    # SQL: el caller pidió include_sql?
    sql_query = raw.get("sql_query") if request.include_sql else None

    error = raw.get("error")
    validation_status = _derive_validation_status(
        sql_query=sql_query,
        error=error,
        intent=raw.get("intent"),
    )

    return AgentResponse(
        answer=raw.get("answer", ""),
        sql_query=sql_query,
        results=results,
        rows_returned=len(results),
        intent=raw.get("intent"),
        schema_source=raw.get("schema_source"),
        schema_tables=raw.get("schema_table_names", []) or [],
        validation_status=validation_status,
        error=error,
        retry_count=int(raw.get("retry_count", 0)),
        latency_ms=agent_latency_ms,
        model_used=settings.gemini_model,
        session_id=session_id,
        trace_url=raw.get("trace_url"),
    )
