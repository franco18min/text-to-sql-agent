"""
executor: corre la SQL validada contra Databricks.

Si la validación falló, no se ejecuta (skip).
Si falla la ejecución (timeout, syntax error en runtime, etc.),
captura el error y lo devuelve para que el agente decida retry.

Devuelve:
- `execution_result`: lista de filas (dicts)
- `execution_error`: mensaje de error si falló
- `retry_count`: incrementado en +1 si falló
"""
from app.config import settings
from app.core.db import execute_query
from app.agent.retry import record_retry_failure
from app.agent.sql_limit import cap_sql_query
from app.agent.state import AgentState


def executor_node(state: AgentState) -> dict:
    if not state.get("sql_valid"):
        return {
            "execution_result": [],
            "execution_error": "skipped (validation failed)",
            "retry_count": state.get("retry_count", 0),
        }

    sql = cap_sql_query(state["sql_query"], settings.max_result_rows)
    try:
        rows = execute_query(sql)
        return {
            "execution_result": rows,
            "execution_error": "",
            "retry_count": state.get("retry_count", 0),
        }
    except Exception as e:
        error = str(e)[:500]
        return {
            "execution_result": [],
            "execution_error": error,
            **record_retry_failure(state, sql, error),
        }
