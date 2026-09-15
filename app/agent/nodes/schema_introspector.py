"""
schema_introspector: trae el contexto de schema para el LLM.

Strategy híbrido (Fase 6):
- Por default: `build_schema_context()` con SHOW TABLES + DESCRIBE TABLE
  (rápido, funciona para <20 tablas)
- Opcional: si `use_vector_search=True` y el endpoint está configurado,
  usar Databricks Vector Search para retrieval semántico (escala a >100 tablas)

Para activar Vector Search: ver docstring de `app.core.vector_search`.
Devuelve:
- `schema_context`: string DDL-like listo para el prompt
- `schema_source`: de dónde salió ("show_describe" o "vector_search")
- `schema_table_names`: lista de tablas (para citations después)
"""
from app.config import settings
from app.core.schema import build_schema_context, count_tables, list_tables
from app.agent.state import AgentState
from app.observability import log_metric, start_span


def schema_introspector_node(state: AgentState) -> dict:
    catalog = settings.databricks_catalog
    schema = settings.databricks_schema
    question = state["question"]

    # Decidir strategy: Vector Search solo si está activado Y hay muchas tablas
    use_vector_search = (
        bool(settings.databricks_vector_search_endpoint)
        and bool(settings.databricks_vector_search_index)
        and count_tables(catalog, schema) > settings.schema_retrieval_threshold
    )

    with start_span("schema_introspector", use_vector_search=use_vector_search):
        if use_vector_search:
            try:
                from app.core.vector_search import (
                    build_schema_context_from_chunks,
                    search_similar_schema_chunks,
                )
                chunks = search_similar_schema_chunks(question, k=5)
                schema_ctx, table_names = build_schema_context_from_chunks(
                    chunks, catalog, schema
                )
                source = "vector_search"
                log_metric("schema_introspector.chunks_retrieved", len(chunks))
            except Exception:
                # Fallback: Vector Search failed — SHOW/DESCRIBE, closed-set source token
                schema_ctx = build_schema_context(catalog, schema)
                table_names = [f"{catalog}.{schema}.{t}" for t in list_tables(catalog, schema)]
                source = "show_describe"
        else:
            schema_ctx = build_schema_context(catalog, schema)
            table_names = [f"{catalog}.{schema}.{t}" for t in list_tables(catalog, schema)]
            source = "show_describe"

    return {
        "schema_context": schema_ctx,
        "schema_source": source,
        "schema_table_names": table_names,
    }
