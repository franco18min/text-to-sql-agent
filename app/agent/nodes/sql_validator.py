"""
sql_validator: gatekeeper de seguridad antes de ejecutar SQL.

Usa `app.core.sql_safety.validate_sql` (blocklist + AST + length + comments)
como primera línea de defensa. Si pasa, hace un EXPLAIN dry-run contra
el warehouse para validar que la query parsea bien.

Devuelve:
- `sql_valid`: bool
- `validation_error`: mensaje de error si no pasó
- `dry_run_result`: output de EXPLAIN (si pasó la primera capa)
"""
from app.config import settings
from app.core.db import execute_query
from app.core.sql_safety import validate_sql
from app.agent.retry import record_retry_failure
from app.agent.sql_limit import cap_sql_query
from app.agent.state import AgentState


def sql_validator_node(state: AgentState) -> dict:
    sql = state.get("sql_query", "").strip()

    # 1) Validación estática (blocklist + sqlparse + length + comments)
    valid, error = validate_sql(sql)
    if not valid:
        return {
            "sql_valid": False,
            "validation_error": error,
            "dry_run_result": "",
            **record_retry_failure(state, sql, error),
        }

    # 2) Persist LIMIT-capped SQL so EXPLAIN and execute share the same string
    safe_sql = cap_sql_query(sql, settings.max_result_rows)

    # 3) Dry-run con EXPLAIN para validar que parsea en el warehouse
    try:
        execute_query(f"EXPLAIN {safe_sql}", fetch=False)
        return {
            "sql_valid": True,
            "validation_error": "",
            "dry_run_result": "EXPLAIN OK",
            "sql_query": safe_sql,
        }
    except Exception as e:
        error = f"EXPLAIN failed: {str(e)[:200]}"
        return {
            "sql_valid": False,
            "validation_error": error,
            "dry_run_result": str(e)[:500],
            **record_retry_failure(state, sql, error),
        }
