"""
give_up: nodo terminal cuando el agente agotó los retries.

Después de N intentos (default 3) fallidos (validación o ejecución),
el router lleva al usuario acá en vez de seguir gastando tokens.
"""
from app.agent.state import AgentState


def give_up_node(state: AgentState) -> dict:
    err = state.get("validation_error") or state.get("execution_error") or "unknown error"
    return {
        "final_response": (
            f"Lo siento, no pude responder a tu pregunta después de "
            f"{state.get('retry_count', 0)} intentos. "
            f"Último error: {err[:300]}. "
            f"Última query intentada: {state.get('sql_query', '')[:200]}. "
            f"Probá reformular la pregunta o contactame si querés que te ayude "
            f"a ajustar el prompt del agente."
        ),
    }
