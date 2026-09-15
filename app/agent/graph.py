"""
LangGraph state machine del agente Text-to-SQL (Databricks + Gemini).

Flujo:
    START → intent_classifier → [chitchat|clarification|schema_introspector]
    schema_introspector → sql_generator → sql_validator
    sql_validator → [valid → executor | invalid → sql_generator (retry) | max_retries → give_up]
    executor → [success → response_formatter | error → sql_generator (retry) | max_retries → give_up]
    response_formatter → memory_updater → END
    chitchat / clarification / give_up → memory_updater → END

Por qué LangGraph y no LangChain: necesitamos ciclos y decisiones
condicionales explícitas para el auto-corrección. LangGraph modela el
state machine directamente, LangChain exige hacks.
"""
import time

from langgraph.graph import END, StateGraph

from app.agent.state import AgentState, make_initial_state
from app.agent.edges import (
    route_by_execution,
    route_by_intent,
    route_by_validation,
)

# Nodos
from app.agent.nodes.chitchat import chitchat_node
from app.agent.nodes.clarification import clarification_node
from app.agent.nodes.executor import executor_node
from app.agent.nodes.give_up import give_up_node
from app.agent.nodes.intent_classifier import intent_classifier_node
from app.agent.nodes.memory_updater import memory_updater_node
from app.agent.nodes.response_formatter import response_formatter_node
from app.agent.nodes.schema_introspector import schema_introspector_node
from app.agent.nodes.sql_generator import sql_generator_node
from app.agent.nodes.sql_validator import sql_validator_node


def build_graph():
    """Construye y compila el state machine del agente."""
    workflow = StateGraph(AgentState)

    # ----- Agregar nodos -----
    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("schema_introspector", schema_introspector_node)
    workflow.add_node("sql_generator", sql_generator_node)
    workflow.add_node("sql_validator", sql_validator_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("response_formatter", response_formatter_node)
    workflow.add_node("memory_updater", memory_updater_node)
    workflow.add_node("chitchat", chitchat_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("give_up", give_up_node)

    # ----- Entry point -----
    workflow.set_entry_point("intent_classifier")

    # ----- Edge condicional después de intent_classifier -----
    workflow.add_conditional_edges(
        "intent_classifier",
        route_by_intent,
        {
            "schema_introspector": "schema_introspector",
            "chitchat": "chitchat",
            "clarification": "clarification",
        },
    )

    # ----- Pipeline principal (lineal) -----
    workflow.add_edge("schema_introspector", "sql_generator")
    workflow.add_edge("sql_generator", "sql_validator")

    # ----- Edge condicional después de sql_validator -----
    workflow.add_conditional_edges(
        "sql_validator",
        route_by_validation,
        {
            "executor": "executor",
            "sql_generator": "sql_generator",  # retry
            "give_up": "give_up",
        },
    )

    # ----- Edge condicional después de executor -----
    workflow.add_conditional_edges(
        "executor",
        route_by_execution,
        {
            "response_formatter": "response_formatter",
            "sql_generator": "sql_generator",  # retry
            "give_up": "give_up",
        },
    )

    # ----- Edges terminales hacia memory_updater -----
    workflow.add_edge("response_formatter", "memory_updater")
    workflow.add_edge("chitchat", "memory_updater")
    workflow.add_edge("clarification", "memory_updater")
    workflow.add_edge("give_up", "memory_updater")

    # ----- END -----
    workflow.add_edge("memory_updater", END)

    return workflow.compile()


# ----- Entry point público -----
def run_agent(question: str, session_id: str) -> dict:
    """
    Punto de entrada principal del agente.

    Args:
        question: pregunta del usuario en lenguaje natural.
        session_id: id de sesión (para memory multi-turn persistente).

    Returns:
        Dict con el state final: answer, sql_query, results, error,
        retry_count, latency_ms, session_id.
    """
    # Cargar history de session memory (si existe)
    from app.core.memory import get_history
    try:
        prior_history = get_history(session_id, limit=10)
        # Formatear a la forma corta que el prompt espera: {role, content}
        short_history = [{"role": h["role"], "content": h["content"]} for h in prior_history]
    except Exception:
        # Si falla (ej. DB no inicializada), arrancar vacío
        short_history = []

    graph = build_graph()
    initial = make_initial_state(
        question=question,
        session_id=session_id,
    )
    initial["conversation_history"] = short_history
    t0 = time.perf_counter()
    final = graph.invoke(initial)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "answer": final.get("final_response", ""),
        "sql_query": final.get("sql_query"),
        "results": final.get("execution_result", []),
        "error": final.get("execution_error") or final.get("validation_error"),
        "retry_count": final.get("retry_count", 0),
        "latency_ms": latency_ms,
        "session_id": session_id,
        "intent": final.get("intent"),
        "schema_source": final.get("schema_source"),
    }
