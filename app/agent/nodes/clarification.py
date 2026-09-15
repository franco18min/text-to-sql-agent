"""
clarification: nodo terminal cuando la pregunta es ambigua.

No llama al LLM. Devuelve un mensaje pidiendo reformulación con pistas
de qué se puede preguntar.
"""
from app.agent.state import AgentState


def clarification_node(state: AgentState) -> dict:
    return {
        "final_response": (
            "No me queda clara tu pregunta. ¿Podés reformularla? "
            "Puedo responder preguntas sobre la base de datos de ejemplo "
            "`samples.tpch` (TPC-H): clientes, órdenes, partes, proveedores, "
            "naciones, regiones. Por ejemplo: '¿Cuántos clientes hay en USA?' "
            "o 'Top 5 clientes por gasto total'."
        ),
    }
