# Arquitectura y decisiones tecnicas

## Stack en una linea

LangGraph (state machine) + Google Gemini (LLM) + Databricks SQL (target) + MLflow (tracing) + FastAPI (REST) + Streamlit (UI).

## Por que LangGraph y no LangChain

Necesitamos **ciclos explicitos** para auto-correccion (si el SQL falla, volver al generador con el feedback). LangGraph modela eso como un grafo de estados con edges condicionales. LangChain exige hacks (`AgentExecutor` con `handle_parsing_errors=True`).

Tambien: LangGraph tiene tipos de estado (`TypedDict`) claros, lo que hace que los nodos sean funciones puras `(state) -> dict` faciles de testear.

## Por que Gemini free tier

Costo: USD 0. Tiene alias `-latest` que escoge la version mas nueva automaticamente. `gemini-2.0-flash-exp` y otros versionados explicitos estan **bloqueados para nuevos usuarios** desde 2025 — siempre usar `gemini-flash-lite-latest` o `gemini-flash-latest`.

Limitacion: rate limits. 30 preguntas del eval tomaron ~15 min (25s p50 por pregunta, pero algunos pegan en 429 y esperan).

## Por que Databricks Free Edition + `samples.tpch`

Alternativas evaluadas:
- **SQLite + Chinook** (el starter original): descartado en Fase 2 porque queremos algo que un Data Engineer reconozca y que escale a millones de filas.
- **Postgres local**: descartado porque requiere setup de infra.
- **Databricks Free Edition + `samples.tpch`**: nativo del workspace, 8 tablas canonicas, millones de filas, cero ETL.

`samples.tpch` es la base TPC-H estandar de data warehousing. Cualquier entrevista de data menciona revenue por nation, top customers, etc. — todo cae naturalmente en este schema.

## Schema retrieval: SHOW TABLES + DESCRIBE

`information_schema.tables` y `information_schema.columns` **no ven las tablas `samples.*`** porque son legacy hive_metastore en Free Edition (no Unity Catalog). Por eso el agente resuelve el schema con:

```sql
SHOW TABLES IN samples.tpch
DESCRIBE TABLE samples.tpch.customer
```

Es Spark SQL nativo, ve ambos mundos (legacy + UC), y funciona en workspaces Premium con UC tambien.

## Guardrail de SQL: 4 capas

1. **Intent classifier** — si la pregunta es claramente chitchat ("hola, como estas?"), no genera SQL.
2. **Blocklist de keywords** — DROP/DELETE/UPDATE/INSERT/TRUNCATE/ALTER/CREATE/GRANT/REVOKE/EXEC/PRAGMA/ATTACH/DETACH/VACUUM. Tambien rechaza `--` y `/* */` (comentarios) y multi-statement (`;` adentro de la query).
3. **`sqlparse`** — parsea el SQL y verifica que sea un solo `SELECT` (o `WITH ... SELECT`).
4. **LIMIT cap** — `add_limit_if_missing` agrega `LIMIT 1000` si no hay; si hay `LIMIT 10000`, lo baja a 1000. Esto es defense contra queries que tiran millones de filas.
5. **EXPLAIN dry-run** — el validator corre `EXPLAIN` contra el warehouse antes de ejecutar; si Spark rechaza el plan, no llega al executor.

Defense in depth: aunque el validator falle, el driver de Databricks se puede configurar read-only a nivel de PAT.

## Auto-correccion: hasta 3 retries (exceptions only)

```
sql_validator --[invalid / EXPLAIN error]--> sql_generator  (retry 1)
                --[max_retries]--> give_up

executor      --[exception / error]--> sql_generator    (retry 1)
                --[max_retries]--> give_up
```

Retry dispara solo ante **exceptions** o errores de validacion/ejecucion. Un result set vacio es success (no retry). El feedback que vuelve al generador incluye el error exacto de Databricks (columna inexistente, syntax error, timeout). El LLM lo usa para regenerar.

## MLflow: degraded to no-op

`mlflow.set_tracking_uri("databricks")` requiere el SDK de Databricks autenticado. Cuando corremos local sin `databricks auth login`, el SDK falla. En vez de romper la app, el wrapper degrada a **no-op silencioso** (cacheado por proceso):

```python
def _is_mlflow_usable() -> bool:
    global _mlflow_available
    if _mlflow_available is not None:
        return _mlflow_available
    try:
        with mlflow.start_span(name="__health_check__"):
            pass
        _mlflow_available = True
    except Exception:
        _mlflow_available = False
    return _mlflow_available
```

Esto permite que la app corra con o sin auth, y cuando se deploya con un PAT que tiene acceso al tracking server, automaticamente empieza a loggear.

## Session memory: dual backend

- **`in_memory`** (default): SQLite en `data/db/sessions.db`. Cero setup, funciona offline.
- **`delta`** (para produccion): tabla Delta en `samples.tpch.agent_sessions`. Persiste en el lakehouse, compartible entre deployments.

La interfaz es la misma (`save_turn`, `get_history`, `clear_session`) — solo cambia el backend.

## Por que FastAPI + Streamlit (no solo uno)

- **FastAPI** es la API formal. Tiene tipos Pydantic, OpenAPI auto, lifespan, CORS, health checks. Es lo que deployarias en un servidor.
- **Streamlit** es el demo rapido. No compite con FastAPI — lo consume. Pensado para uso local o demo publico.

Un usuario de negocio abre Streamlit. Un sistema automatizado llama a FastAPI. Mismo agente, dos interfaces.

## Decisiones que NO tomamos (y por que)

- **LangSmith en vez de MLflow**: descartado porque MLflow esta nativo en Databricks (mismo tracking server, sin auth extra). LangSmith es bueno pero requiere signup.
- **Vector Search para schema retrieval** (cuando hay >20 tablas): implementado en `app/core/vector_search.py` como opt-in. Para `samples.tpch` (8 tablas) no aporta — `SHOW TABLES` + `DESCRIBE` es mas rapido y exacto.
- **GPT-4 / Claude**: descartado por costo. Gemini free tier da resultados comparables en este dominio.
- **Streaming de tokens**: descartado para v1. La latencia es ~25s total, dominada por SQL generation + execution. El usuario espera, no streamea.
