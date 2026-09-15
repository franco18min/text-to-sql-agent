"""
GET /health — health check.

Pingea:
- Databricks: `SELECT 1` (via app.core.db.execute_query)
- LLM: generate una palabra con un timeout corto (skipeable si skip_llm=true)

Devuelve:
- status: "ok" | "degraded" | "down"
- databricks_reachable, llm_reachable (opcional, los flags)
- detail: mensaje legible si algo está caído
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app import __version__
from app.config import settings
from app.models.response import HealthResponse


router = APIRouter(tags=["health"])


def _ping_databricks() -> tuple[bool, str | None]:
    try:
        from app.core.db import execute_query
        rows = execute_query("SELECT 1 AS ok", fetch=True)
        if rows and rows[0].get("ok") == 1:
            return True, None
        return False, f"SELECT 1 devolvió inesperado: {rows}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _ping_llm() -> tuple[bool, str | None]:
    try:
        from app.core.llm import generate
        out = generate("Respond only with the word 'ok'.", temperature=0.0, max_tokens=8)
        if "ok" in (out or "").lower():
            return True, None
        return False, f"LLM respondió algo inesperado: {(out or '')[:60]!r}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


@router.get("/health", response_model=HealthResponse)
async def health(
    deep: bool = Query(default=False, description="Si true, pingea Databricks y el LLM"),
    skip_llm: bool = Query(default=False, description="Saltea el ping al LLM (útil en CI)"),
):
    """
    Health check rápido.

    - Sin `deep=true`: solo valida que las env vars estén bien.
    - Con `deep=true`: pingea Databricks (SELECT 1) y el LLM (1 token).
    """
    base = HealthResponse(
        status="ok",
        version=__version__,
        model=settings.gemini_model,
        databricks_configured=settings.is_databricks_configured,
        memory_backend=settings.memory_type,
    )

    if not deep:
        if not settings.is_databricks_configured:
            return base.model_copy(update={
                "status": "degraded",
                "detail": "Databricks no configurado (faltan env vars)",
            })
        return base

    # Deep check
    db_ok, db_err = _ping_databricks()
    llm_ok: bool | None = None
    llm_err: str | None = None
    if not skip_llm:
        llm_ok, llm_err = _ping_llm()

    if db_ok and (llm_ok is None or llm_ok):
        status_str = "ok"
        detail = None
    elif db_ok and not llm_ok:
        status_str = "degraded"
        detail = f"Databricks OK, LLM falló: {llm_err}"
    elif not db_ok and (llm_ok is None or llm_ok):
        status_str = "degraded"
        detail = f"Databricks falló: {db_err}, LLM OK"
    else:
        status_str = "down"
        detail = f"Databricks: {db_err}; LLM: {llm_err}"

    return base.model_copy(update={
        "status": status_str,
        "databricks_reachable": db_ok,
        "llm_reachable": llm_ok,
        "detail": detail,
    })
