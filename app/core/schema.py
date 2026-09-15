"""
Schema introspection for Databricks.

Lee metadata de tablas/columnas con `SHOW TABLES` + `DESCRIBE TABLE EXTENDED`
y la formatea como contexto (CREATE TABLE-like DDL) para pasar al LLM del agente.

Por qué `SHOW TABLES` y no `information_schema.tables`:
- En Databricks Free Edition, `samples.*` son datasets legacy del
  hive_metastore que NO aparecen en `information_schema`.
- `SHOW TABLES` los ve siempre (es la sintaxis Spark nativa).
- Funciona también en workspaces Premium con Unity Catalog.

Approach futuro (Fase 6): Vector Search sobre la metadata cuando el
número de tablas supere `schema_retrieval_threshold`.
"""
from functools import lru_cache

from app.config import settings
from app.core.db import execute_query


# ----- Listado de tablas -----

def list_tables(catalog: str, schema: str) -> list[str]:
    """
    Lista tablas en catalog.schema usando `SHOW TABLES`.

    Por qué `SHOW TABLES` y no `information_schema.tables`:
    - En Databricks Free Edition, `samples.*` son datasets legacy
      del hive_metastore que no aparecen en `information_schema`.
    - `SHOW TABLES` los ve siempre (es la sintaxis Spark nativa).
    - Cuando Franco conecte a un workspace real con UC, sigue funcionando.

    Returns:
        Lista de nombres de tabla (sin catalog.schema prefix).
    """
    rows = execute_query(f"SHOW TABLES IN {catalog}.{schema}")
    # SHOW TABLES devuelve: database, tableName, isTemporary
    return [r["tableName"] for r in rows if not r.get("isTemporary")]


# ----- Descripción de una tabla -----

def describe_table(catalog: str, schema: str, table: str) -> list[dict]:
    """
    Devuelve las columnas de una tabla con tipo y comentario.

    Usa `DESCRIBE TABLE` (formato simple de Spark SQL) que devuelve una
    fila por columna con `(col_name, data_type, comment)`. Más confiable
    que `DESCRIBE TABLE EXTENDED AS JSON` cuyo formato varía según la
    versión de Databricks y el tipo de tabla (Delta/Parquet/view).

    `DESCRIBE TABLE EXTENDED` agrega metadata adicional del storage
    después de las columnas, separado por una fila vacía — lo ignoramos
    porque no aporta al LLM.

    Returns:
        Lista de dicts con keys: col_name, data_type, comment, nullable
    """
    fqtn = f"{catalog}.{schema}.{table}"
    rows = execute_query(f"DESCRIBE TABLE {fqtn}")
    out = []
    for r in rows:
        col_name = r.get("col_name")
        data_type = r.get("data_type")
        # Filas vacías o de metadata delimitan el fin de las columnas
        if not col_name or not data_type:
            continue
        # Rows de EXTENDED metadata vienen con col_name que empieza con '#'
        if col_name.startswith("#"):
            break
        out.append({
            "col_name": col_name,
            "data_type": data_type,
            "comment": r.get("comment") or "",
            "nullable": True,  # DESCRIBE simple no devuelve nulabilidad
        })
    return out


# ----- DDL builder -----

def build_table_ddl(catalog: str, schema: str, table: str) -> str:
    """
    Genera un DDL tipo `CREATE TABLE` (sin storage clause) para una tabla.

    Formato optimizado para que el LLM entienda estructura rápidamente:
    column_name TYPE [-- comment]
    """
    cols = describe_table(catalog, schema, table)
    if not cols:
        return f"-- Table {catalog}.{schema}.{table} not found or empty"

    col_lines = []
    for c in cols:
        nullable = "" if c.get("nullable", True) else " NOT NULL"
        comment = f" -- {c['comment']}" if c.get("comment") else ""
        col_lines.append(f"  {c['col_name']} {c['data_type']}{nullable}{comment}")

    fqtn = f"{catalog}.{schema}.{table}"
    return f"CREATE TABLE {fqtn} (\n" + ",\n".join(col_lines) + "\n);"


# ----- Context builder -----

def build_schema_context(
    catalog: str | None = None,
    schema: str | None = None,
    table_filter: list[str] | None = None,
) -> str:
    """
    Genera el bloque de contexto de schema para el prompt del LLM.

    Args:
        catalog: UC catalog (default: settings.databricks_catalog).
        schema: UC schema (default: settings.databricks_schema).
        table_filter: si se pasa, solo se incluyen esas tablas. Si no,
            se listan todas las del schema.

    Returns:
        String con un comentario de header y los DDLs concatenados.
        Si no hay tablas, devuelve un mensaje explícito.
    """
    catalog = catalog or settings.databricks_catalog
    schema = schema or settings.databricks_schema

    tables = table_filter or list_tables(catalog, schema)
    if not tables:
        return f"-- No tables found in {catalog}.{schema}"

    blocks = [build_table_ddl(catalog, schema, t) for t in tables]
    header = f"-- Schema for {catalog}.{schema} ({len(tables)} tables)\n\n"
    return header + "\n\n".join(blocks)


# ----- Cached version (uso: cuando se sabe que el schema no cambia) -----

@lru_cache(maxsize=1)
def get_full_schema_context() -> str:
    """
    Cached version del schema completo.

    Útil cuando el LLM recibe el mismo context repetidas veces en una
    misma sesión. Cache vive lo que vive el proceso Python; si el schema
    cambia, hay que reiniciar el proceso.
    """
    return build_schema_context()


# ----- Stats para routing (Fase 6: decidir Vector Search vs info_schema) -----

def count_tables(catalog: str | None = None, schema: str | None = None) -> int:
    """Cuenta cuántas tablas hay. Usado para decidir schema retrieval strategy."""
    catalog = catalog or settings.databricks_catalog
    schema = schema or settings.databricks_schema
    return len(list_tables(catalog, schema))
