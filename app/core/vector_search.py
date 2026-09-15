"""
Databricks Vector Search wrapper para schema retrieval.

Por qué Vector Search (no `SHOW TABLES` directo):
- Cuando tenés >20-50 tablas, mandar todo el DDL al LLM es caro
  y ruidoso. Vector Search te trae solo las 5-10 tablas relevantes
  según la pregunta del usuario (similaridad semántica).
- samples.tpch tiene solo 8 tablas, así que `SHOW TABLES` +
  `build_schema_context()` alcanza. PERO la infraestructura queda
  lista para cuando conectes a un workspace con UC real que tenga
  cientos de tablas.

Setup necesario (UNA VEZ) para activarlo:

1. Crear endpoint en Databricks UI:
   Compute > Vector Search > Create Endpoint
   Nombre: text2sql-schema-endpoint (el del .env)
   Tipo: Standard

2. Crear Delta table con la metadata del schema (chunks + embeddings).
   El script `scripts/build_schema_index.py` (Fase 9) lo hace por vos.
   Genera rows con campos: chunk_id, table_name, column_name,
   chunk_text, embedding (vector de Gemini text-embedding-004).

3. Crear el Delta Sync Index apuntando a esa table:
   from databricks.ai_search.client import AISearchClient
   client = AISearchClient()
   client.create_delta_sync_index(
       endpoint_name="text2sql-schema-endpoint",
       index_name="text2sql_agent.schema_metadata",
       primary_key="chunk_id",
       embedding_source_column="chunk_text",
       embedding_model_endpoint_name="databricks-gte-large-en",
   )

4. Activar en `app/agent/nodes/schema_introspector.py`:
   Cambiar `use_vector_search = False` por `use_vector_search = True`

Por qué `databricks-ai-search` (no `databricks-vectorsearch`):
- Según Databricks 2026, `databricks-vectorsearch>=0.75` es un
  thin re-export de `databricks-ai-search>=0.78`. El viejo
  `VectorSearchClient` está deprecated.
"""
from functools import lru_cache
from typing import Any

from app.config import settings


@lru_cache(maxsize=1)
def get_ai_search_client():
    """
    Singleton del AISearchClient.

    Lanza ImportError si `databricks-ai-search` no está instalado.
    """
    try:
        from databricks.ai_search.client import AISearchClient
    except ImportError as e:
        raise ImportError(
            "databricks-ai-search no está instalado. "
            "pip install databricks-ai-search>=0.78"
        ) from e
    return AISearchClient()


def search_similar_schema_chunks(
    question: str,
    *,
    k: int = 5,
    endpoint: str | None = None,
    index: str | None = None,
) -> list[dict]:
    """
    Busca los top-k chunks de schema metadata más similares a la pregunta.

    Args:
        question: pregunta en lenguaje natural del usuario.
        k: cantidad de chunks a devolver.
        endpoint: nombre del endpoint (default: settings).
        index: full name del index (default: settings).

    Returns:
        Lista de dicts con keys: chunk_id, table_name, column_name,
        chunk_text, score.

    Raises:
        ImportError: si databricks-ai-search no está instalado.
        RuntimeError: si el index no está configurado o el endpoint
            no está disponible.
    """
    client = get_ai_search_client()
    ep = endpoint or settings.databricks_vector_search_endpoint
    idx = index or settings.databricks_vector_search_index

    if not ep or not idx:
        raise RuntimeError(
            "Vector Search no está configurado. Set "
            "DATABRICKS_VECTOR_SEARCH_ENDPOINT y "
            "DATABRICKS_VECTOR_SEARCH_INDEX en .env. "
            "O cambiá use_vector_search=False en schema_introspector.py."
        )

    # El SDK de Databricks Vector Search tiene una API typed.
    # similarity_search devuelve una estructura con columns y results.
    try:
        response = client.similarity_search(
            endpoint_name=ep,
            index_name=idx,
            query_text=question,
            num_results=k,
        )
    except Exception as e:
        raise RuntimeError(
            f"Error querying Vector Search index {idx} on endpoint {ep}: {e}"
        ) from e

    # Normalizar la respuesta (el formato puede variar según versión)
    chunks: list[dict] = []
    # SDK moderno devuelve response.data dict-style; manejamos ambos
    data = getattr(response, "data", response)
    manifest = getattr(data, "manifest", None)
    if manifest:
        # Versión con manifest
        for col in getattr(manifest, "columns", []):
            pass  # placeholder para manifest

    result_array = getattr(data, "result", None) or getattr(data, "results", None)
    if result_array is None and isinstance(data, dict):
        result_array = data.get("result") or data.get("results")

    if result_array is None:
        # Última instancia: el response mismo es un iterable
        try:
            result_array = list(data)
        except TypeError:
            return []

    for row in result_array:
        # row puede ser dict, NamedTuple, o dataclass
        if isinstance(row, dict):
            chunks.append({
                "chunk_id": row.get("chunk_id"),
                "table_name": row.get("table_name"),
                "column_name": row.get("column_name"),
                "chunk_text": row.get("chunk_text"),
                "score": row.get("score", 0.0),
            })
        else:
            chunks.append({
                "chunk_id": getattr(row, "chunk_id", None),
                "table_name": getattr(row, "table_name", None),
                "column_name": getattr(row, "column_name", None),
                "chunk_text": getattr(row, "chunk_text", None),
                "score": getattr(row, "score", 0.0),
            })

    return chunks


def build_schema_context_from_chunks(
    chunks: list[dict],
    catalog: str,
    schema: str,
) -> tuple[str, list[str]]:
    """
    Construye el context para el LLM a partir de chunks del Vector Search.

    Agrupa chunks por tabla, deduplica, y genera un DDL-like
    context con solo las tablas relevantes.

    Returns:
        Tupla (schema_context, list_of_full_table_names).
    """
    if not chunks:
        return "", []

    # Agrupar chunks por tabla
    by_table: dict[str, list[dict]] = {}
    for c in chunks:
        tbl = c.get("table_name")
        if not tbl:
            continue
        by_table.setdefault(tbl, []).append(c)

    table_names = list(by_table.keys())
    blocks = []
    for tbl, tbl_chunks in by_table.items():
        # Cada chunk contiene info de una columna o de la tabla entera
        # El formato esperado es: "table: customer | cols: c_custkey bigint PK, c_name string..."
        col_descriptions = [
            c["chunk_text"] for c in tbl_chunks if c.get("chunk_text")
        ]
        if col_descriptions:
            block = (
                f"CREATE TABLE {catalog}.{schema}.{tbl} (\n"
                + ",\n".join(f"  -- {desc}" for desc in col_descriptions)
                + "\n);"
            )
        else:
            block = f"CREATE TABLE {catalog}.{schema}.{tbl} ();"
        blocks.append(block)

    header = (
        f"-- Schema context (retrieved via Vector Search, "
        f"{len(table_names)} relevant tables)\n\n"
    )
    return header + "\n\n".join(blocks), [
        f"{catalog}.{schema}.{t}" for t in table_names
    ]
