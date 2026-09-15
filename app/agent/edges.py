"""
Funciones de routing para edges condicionales del grafo LangGraph.

Cada función recibe un AgentState y devuelve el nombre del próximo nodo.
Estas se enchufan en `workflow.add_conditional_edges(...)`.
"""
from app.agent.state import AgentState
from app.config import settings


def route_by_intent(state: AgentState) -> str:
    """Decide el primer paso después de clasificar intención."""
    intent = state.get("intent", "sql_query")
    if intent == "sql_query":
        return "schema_introspector"
    if intent == "chitchat":
        return "chitchat"
    if intent == "clarification":
        return "clarification"
    # default: tratar como sql
    return "schema_introspector"


def route_by_validation(state: AgentState) -> str:
    """Después de validar SQL: ejecutar, retry, o rendirse."""
    if state.get("sql_valid") and not state.get("validation_error"):
        return "executor"
    if state.get("retry_count", 0) >= settings.max_retries:
        return "give_up"  # render error al usuario con lo que tengamos
    return "sql_generator"  # retry con feedback


def route_by_execution(state: AgentState) -> str:
    """Después de ejecutar: formatear, retry, o rendirse."""
    if not state.get("execution_error"):
        return "response_formatter"
    if state.get("retry_count", 0) >= settings.max_retries:
        return "give_up"
    return "sql_generator"  # retry con error de ejecución como feedback


def should_continue_after_retry(state: AgentState) -> str:
    """Después de un retry, ¿se agotaron los intentos?"""
    if state.get("retry_count", 0) >= 3:
        return "give_up"
    return "sql_validator"
