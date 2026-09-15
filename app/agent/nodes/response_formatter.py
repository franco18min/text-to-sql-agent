"""
response_formatter: el LLM explica los resultados en lenguaje natural.

Si no hay resultados o hubo error, genera un mensaje sin llamar al LLM
(ahorra tokens y latencia).

Devuelve:
- `final_response`: string con la respuesta al usuario
"""
from app.config import settings
from app.agent.prompts import RESPONSE_FORMATTER_PROMPT
from app.core.llm import generate
from app.agent.state import AgentState


def _truncate_rows(rows: list[dict], max_rows: int) -> str:
    """Trunca filas para no mandar 10k rows al LLM."""
    if not rows:
        return "(no rows)"
    sample = rows[:max_rows]
    return str(sample)


def response_formatter_node(state: AgentState) -> dict:
    # Si hubo error de ejecución, mensaje directo
    err = state.get("execution_error")
    if err and err != "" and err != "skipped (validation failed)":
        return {
            "final_response": (
                f"No pude ejecutar la query. "
                f"Error: {err[:300]}. "
                f"Query intentada: {state.get('sql_query', '')[:200]}"
            ),
        }

    # Si no hay resultados
    if not state.get("execution_result"):
        return {
            "final_response": (
                "La query se ejecutó correctamente pero no devolvió resultados. "
                "Si esperabas datos, probá reformular la pregunta o relajar filtros."
            ),
        }

    # Caso normal: LLM explica
    prompt = RESPONSE_FORMATTER_PROMPT.format(
        max_rows=settings.max_result_rows,
        question=state["question"],
        sql_query=state.get("sql_query", ""),
        execution_result=_truncate_rows(
            state["execution_result"], settings.max_result_rows
        ),
        schema_context=state.get("schema_context", ""),
    )
    text = generate(prompt, temperature=0.0, max_tokens=1024)
    return {"final_response": text}
