"""
Response schemas para la API.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ============================================================
# /query  — respuesta principal del agente
# ============================================================
class AgentResponse(BaseModel):
    """Body de respuesta del POST /query"""

    # Output principal
    answer: str = Field(..., description="Respuesta en lenguaje natural")
    sql_query: Optional[str] = Field(default=None, description="SQL ejecutado (si include_sql=true)")
    results: list[dict] = Field(default_factory=list, description="Filas del resultado (si include_results=true)")
    rows_returned: int = Field(default=0, description="Cantidad de filas en results")

    # Routing
    intent: Optional[Literal["sql_query", "chitchat", "clarification", "give_up"]] = Field(
        default=None,
        description="Intención clasificada por el agente",
    )

    # Metadata de schema retrieval
    schema_source: Optional[Literal["vector_search", "show_describe", "cache", "none"]] = Field(
        default=None,
        description="Cómo se resolvió el schema de la DB",
    )
    schema_tables: list[str] = Field(
        default_factory=list,
        description="Tablas referenciadas en la query generada",
    )

    # Metadata de validación
    validation_status: Optional[Literal["valid", "invalid", "skipped", "not_applicable"]] = Field(
        default=None,
        description="Resultado del guardrail de SQL",
    )

    # Errores
    error: Optional[str] = Field(default=None, description="Mensaje de error si algo falló")
    retry_count: int = Field(default=0, description="Cantidad de reintentos de auto-corrección")

    # Performance / tracing
    latency_ms: float = Field(..., description="Latencia total del agente")
    model_used: Optional[str] = Field(default=None, description="Modelo LLM usado")
    session_id: str = Field(..., description="ID de sesión (eco del request o generado)")
    trace_url: Optional[str] = Field(default=None, description="URL al trace de MLflow (Fase 6)")


# ============================================================
# /health
# ============================================================
class HealthResponse(BaseModel):
    """Body de GET /health"""

    status: Literal["ok", "degraded", "down"]
    version: str
    model: str
    databricks_configured: bool
    memory_backend: str
    # Detalles opcionales de los pings reales
    databricks_reachable: Optional[bool] = None
    llm_reachable: Optional[bool] = None
    detail: Optional[str] = None


# ============================================================
# /schema
# ============================================================
class SchemaTableInfo(BaseModel):
    """Una tabla en la respuesta de GET /schema"""

    catalog: str
    schema: str
    table: str
    full_name: str
    # HTTP contract (not Spark DESCRIBE keys): name, type, nullable, comment
    columns: list[dict]  # [{name, type, nullable, comment}, ...]
    comment: Optional[str] = None


class SchemaResponse(BaseModel):
    """Body de GET /schema"""

    catalog: str
    schema: str
    tables: list[SchemaTableInfo]
    total_tables: int


# ============================================================
# /sessions
# ============================================================
class HistoryTurn(BaseModel):
    """Un turn en el historial de una sesión."""

    role: Literal["user", "assistant"]
    content: str
    sql: Optional[str] = None
    sql_valid: Optional[bool] = None
    execution_error: Optional[str] = None
    retry_count: int = 0
    latency_ms: float = 0.0
    model_used: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    """Body de GET /sessions/{session_id}"""

    session_id: str
    turn_count: int
    history: list[HistoryTurn]


class SessionSummary(BaseModel):
    """Un session en la respuesta de GET /sessions."""

    session_id: str
    turn_count: int
    first_ts: float
    last_ts: float
    last_question: Optional[str] = None


class SessionsListResponse(BaseModel):
    """Body de GET /sessions."""

    sessions: list[SessionSummary]
    total: int


class SessionActionResponse(BaseModel):
    """Body de POST /sessions (crear) o DELETE /sessions/{id}."""

    session_id: str
    action: Literal["created", "cleared"]
    affected_rows: int = 0
