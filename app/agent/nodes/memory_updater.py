"""
memory_updater: persiste el turno actual en session memory (SQLite o Delta).

Guarda DOS turns por cada invocación del agente:
1. El del user (la pregunta)
2. El del assistant (la respuesta, con el SQL generado)

El session_id viene del state (lo pasa el caller del grafo).

Por qué separar user y assistant: el formato de Turn es uniforme
(ambos tienen role + content) pero los metadatos son distintos
(solo assistant tiene sql, retry_count, etc).
"""
import time

from app.agent.state import AgentState
from app.core.memory import save_turn
from app.config import settings


def memory_updater_node(state: AgentState) -> dict:
    session_id = state.get("session_id", "default")

    # Turn 1: el user
    save_turn(
        session_id=session_id,
        role="user",
        content=state["question"],
    )

    # Turn 2: el assistant
    save_turn(
        session_id=session_id,
        role="assistant",
        content=state.get("final_response", ""),
        sql=state.get("sql_query"),
        sql_valid=state.get("sql_valid"),
        execution_error=state.get("execution_error") or state.get("validation_error"),
        retry_count=state.get("retry_count", 0),
        latency_ms=state.get("latency_ms", 0.0),
        model_used=state.get("model_used") or settings.gemini_model,
    )

    # Devolvemos conversation_history actualizada para que el state
    # del grafo la tenga (por si se usa en el mismo run).
    history = list(state.get("conversation_history", []))
    history.append({"role": "user", "content": state["question"]})
    history.append({
        "role": "assistant",
        "content": state.get("final_response", ""),
        "sql": state.get("sql_query"),
    })
    return {"conversation_history": history}
