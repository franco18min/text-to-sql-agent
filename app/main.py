"""
FastAPI app - Text-to-SQL Agent API (Databricks + LangGraph + Gemini)

Endpoints:
    POST /query                 Hacer una pregunta en lenguaje natural
    GET  /health                Health check (deep opcional: pingea Databricks + LLM)
    GET  /schema                Listar tablas y columnas de samples.tpch
    POST /sessions              Crear una session nueva
    GET  /sessions              Listar sessions recientes
    GET  /sessions/{id}         Historial completo de una session
    DELETE /sessions/{id}       Borrar una session
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import chat, health, sessions
from app.config import settings
from app.models.response import HealthResponse, SchemaResponse


logger = logging.getLogger(__name__)


# ----- Lifespan: configurar MLflow al startup -----
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure MLflow + inicializa SQLite al startup."""
    try:
        from app.observability import configure_mlflow
        configure_mlflow()
        logger.info("MLflow configurado (tracking_uri=%s)", settings.mlflow_tracking_uri)
    except Exception as e:
        # No bloqueamos el startup si MLflow falla — el agente igual corre.
        logger.warning("No se pudo configurar MLflow al startup: %s", e)

    # Inicializar SQLite de session memory (no-op si ya está)
    try:
        from app.core.memory import get_history
        get_history("__init__")
    except Exception:
        pass

    yield

    # Flush async spans al shutdown (best-effort)
    try:
        import mlflow
        if hasattr(mlflow, "flush_trace_async_logging"):
            mlflow.flush_trace_async_logging()
    except Exception:
        pass


# ----- App -----
app = FastAPI(
    title="Text-to-SQL Agent (Databricks)",
    description=(
        "Agente AI que traduce preguntas de negocio a SQL sobre Databricks "
        "(Unity Catalog). Stack: LangGraph + Gemini + Databricks SQL."
    ),
    version=__version__,
    lifespan=lifespan,
)

# ----- CORS — Streamlit local (8501) + Cloud / HF Spaces via regex -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_origin_regex=r"https://.*\.(streamlit\.app|hf\.space)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Routers -----
app.include_router(chat.router)
app.include_router(health.router)
app.include_router(sessions.router)


def _spark_column_to_http(col: dict) -> dict:
    """Map Spark DESCRIBE keys to the HTTP /schema column contract."""
    return {
        "name": col.get("col_name"),
        "type": col.get("data_type"),
        "nullable": col.get("nullable", True),
        "comment": col.get("comment") or "",
    }


# ----- Schema (inline, simple) -----
@app.get("/schema", response_model=SchemaResponse, tags=["meta"])
async def get_schema():
    """
    Devuelve el schema de samples.tpch (o el catalog/schema configurado).
    Usa SHOW TABLES + DESCRIBE TABLE — no information_schema, que no ve
    las tablas legacy hive_metastore en Free Edition.
    """
    from app.core.schema import list_tables, describe_table

    catalog = settings.databricks_catalog
    schema_name = settings.databricks_schema
    try:
        tables = list_tables(catalog, schema_name)
    except Exception as e:
        # Si falla, devolvemos schema vacío en vez de 500 (mejor UX para el chat)
        logger.warning("list_tables falló: %s", e)
        return SchemaResponse(
            catalog=catalog,
            schema=schema_name,
            tables=[],
            total_tables=0,
        )

    out = []
    for table in tables:
        cols = describe_table(catalog, schema_name, table)
        out.append({
            "catalog": catalog,
            "schema": schema_name,
            "table": table,
            "full_name": f"{catalog}.{schema_name}.{table}",
            "columns": [_spark_column_to_http(c) for c in cols],
            "comment": None,
        })

    return SchemaResponse(
        catalog=catalog,
        schema=schema_name,
        tables=out,
        total_tables=len(out),
    )


# ----- Root redirect -----
@app.get("/", tags=["meta"])
async def root():
    return {
        "service": "text-to-sql-agent",
        "version": __version__,
        "docs": "/docs",
        "endpoints": [
            "POST /query",
            "GET  /health",
            "GET  /schema",
            "POST /sessions",
            "GET  /sessions",
            "GET  /sessions/{id}",
            "DELETE /sessions/{id}",
        ],
    }


# ----- Entrypoint local -----
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
