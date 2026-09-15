"""
sql_generator: el LLM genera la query SQL a partir de la pregunta + schema.

Usa el prompt de `prompts.SQL_GENERATOR_PROMPT` con la conversación
y retry history inyectadas. Si la respuesta viene en markdown
```sql ... ```, lo limpia.

Devuelve:
- `sql_query`: SQL limpio
- `sql_explanation`: opcional, lo dejamos vacío por ahora
"""
from app.agent.prompts import SQL_GENERATOR_PROMPT
from app.core.llm import extract_sql, generate
from app.agent.state import AgentState


def _format_history(history: list[dict]) -> str:
    """Formatea conversation_history para el prompt."""
    if not history:
        return "(no previous turns)"
    lines = []
    for h in history[-6:]:  # últimos 3 turnos (6 entries = 3 user+assistant)
        role = h.get("role", "user")
        content = h.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _format_retry_history(retry_history: list[dict]) -> str:
    """Formatea los intentos previos (para feedback de auto-corrección)."""
    if not retry_history:
        return "(first attempt)"
    lines = []
    for r in retry_history:
        attempt = r.get("attempt", "?")
        sql = r.get("sql", "")
        error = r.get("error", "")
        lines.append(f"Attempt {attempt}:")
        lines.append(f"  SQL: {sql[:200]}")
        lines.append(f"  Error: {error[:200]}")
    return "\n".join(lines)


def sql_generator_node(state: AgentState) -> dict:
    prompt = SQL_GENERATOR_PROMPT.format(
        schema_context=state.get("schema_context", "(no schema)"),
        conversation_history=_format_history(state.get("conversation_history", [])),
        retry_history=_format_retry_history(state.get("retry_history", [])),
        question=state["question"],
    )
    raw = generate(prompt, temperature=0.0, max_tokens=1024)
    sql = extract_sql(raw)
    return {
        "sql_query": sql,
        "sql_explanation": "",  # TODO Fase 8: pedirle al LLM que la incluya
    }
