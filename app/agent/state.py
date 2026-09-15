"""
AgentState: el TypedDict que se pasa entre nodos del grafo LangGraph.

Mantener liviano: solo lo que se mueve entre nodos. Memory persistente
vive en otro lado (ver `app.observability.tracing` o `app.core.memory` en Fase 6).
"""
from typing import Literal, TypedDict


class AgentState(TypedDict):
    """Estado del agente Text-to-SQL."""

    # Input
    question: str
    session_id: str

    # Memory (turn-level: últimas N interacciones de la sesión)
    conversation_history: list[dict]

    # Clasificación de intención
    intent: Literal["sql_query", "clarification", "chitchat"]

    # Schema retrieval
    schema_context: str  # DDL o descripción textual de tablas relevantes
    schema_source: Literal["show_describe", "cache", "vector_search", "none"]
    schema_table_names: list[str]  # nombres completos catalog.schema.table

    # SQL generation
    sql_query: str
    sql_explanation: str  # qué hace la query en lenguaje natural

    # SQL validation
    sql_valid: bool
    validation_error: str
    dry_run_result: str  # salida de EXPLAIN (si aplica)

    # Execution
    execution_result: list[dict]
    execution_error: str
    retry_count: int
    retry_history: list[dict]  # [{attempt, sql, error}, ...]

    # Output
    final_response: str
    citations: list[dict]  # tablas/columnas referenciadas

    # Metadata
    trace_id: str
    latency_ms: float
    model_used: str


# Valores por defecto para construir el initial state
def make_initial_state(question: str, session_id: str) -> AgentState:
    """Factory para el estado inicial de un turno nuevo."""
    return {
        "question": question,
        "session_id": session_id,
        "conversation_history": [],
        "intent": "sql_query",  # default, el classifier lo sobreescribe
        "schema_context": "",
        "schema_source": "cache",
        "schema_table_names": [],
        "sql_query": "",
        "sql_explanation": "",
        "sql_valid": False,
        "validation_error": "",
        "dry_run_result": "",
        "execution_result": [],
        "execution_error": "",
        "retry_count": 0,
        "retry_history": [],
        "final_response": "",
        "citations": [],
        "trace_id": "",
        "latency_ms": 0.0,
        "model_used": "",
    }
