"""
SQL safety guardrails.

CRÍTICO: este módulo es la primera línea de defensa contra SQL injection
y operaciones destructivas. Todos los tests en test_sql_safety.py deben pasar
antes de hacer deploy.
"""
import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import Keyword, DML, DDL
from typing import Tuple


DANGEROUS_KEYWORDS = {
    "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE",
    "ALTER", "CREATE", "GRANT", "REVOKE", "REPLACE",
    "EXEC", "EXECUTE", "PRAGMA", "ATTACH", "DETACH",
    "VACUUM", "REINDEX", "LOAD", "SAVEPOINT", "ROLLBACK"
}

ALLOWED_FIRST_KEYWORDS = {"SELECT", "WITH", "EXPLAIN"}


def validate_sql(query: str) -> Tuple[bool, str]:
    """
    Valida que un query SQL sea seguro para ejecutar.

    Returns:
        (is_valid, error_message)
    """
    # 1. Longitud máxima
    if len(query) > 2000:
        return False, "Query excede el largo máximo (2000 caracteres)"

    # 2. Parsear
    try:
        parsed = sqlparse.parse(query)
    except Exception as e:
        return False, f"Error parseando SQL: {e}"

    if not parsed:
        return False, "Query vacío"

    # 3. Verificar cantidad de statements
    if len(parsed) > 1:
        return False, f"Múltiples statements no permitidos ({len(parsed)} encontrados)"

    statement = parsed[0]

    # 4. Verificar que sea un statement reconocido
    if not isinstance(statement, Statement):
        return False, "Query no es un statement SQL válido"

    # 4b. Chequeo temprano de keyword peligrosa al inicio (raw string),
    # antes del check de "primera keyword" — asi el error es accionable
    # cuando sqlparse no reconoce el token (ej. GRANT, REVOKE, PRAGMA).
    first_word = query.strip().split(None, 1)[0].upper() if query.strip() else ""
    if first_word in DANGEROUS_KEYWORDS:
        return False, f"Statement empieza con keyword peligrosa: {first_word}"

    # 5. Verificar primera keyword (via sqlparse)
    first_keyword = None
    for token in statement.flatten():
        if token.ttype in (Keyword, Keyword.DML, Keyword.DDL, Keyword.CTE):
            first_keyword = token.value.upper().strip()
            break
        if token.ttype is DML or token.ttype is DDL:
            first_keyword = token.value.upper().strip()
            break
        if token.ttype is None and token.value.strip():
            # puede ser un identifier
            continue

    if first_keyword not in ALLOWED_FIRST_KEYWORDS:
        return False, f"Solo se permiten queries que empiecen con SELECT, WITH o EXPLAIN. Recibido: {first_keyword or first_word}"

    # 6. Buscar keywords peligrosas en todo el statement
    query_upper = query.upper()
    for keyword in DANGEROUS_KEYWORDS:
        # Buscamos como word boundary para evitar falsos positivos
        # (e.g. "UPDATED_AT" no debería matchear "UPDATE")
        if _contains_keyword(query_upper, keyword):
            return False, f"Keyword peligrosa detectada: {keyword}"

    # 7. Detectar comentarios SQL (posible obfuscation)
    if "--" in query or "/*" in query or "*/" in query:
        return False, "Comentarios SQL no permitidos"

    # 8. Detectar múltiples statements con ;
    if query.strip().count(";") > 1:
        return False, "Múltiples statements separados por ; no permitidos"

    return True, ""


def _contains_keyword(query_upper: str, keyword: str) -> bool:
    """Verifica si una keyword aparece como word boundary."""
    import re
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return bool(re.search(pattern, query_upper))


def add_limit_if_missing(query: str, max_rows: int = 1000) -> str:
    """
    Si el query no tiene LIMIT, agrega uno por seguridad.
    Si tiene LIMIT > max_rows, lo capea a max_rows (defense in depth:
    el LLM no debería pedir 1M de filas, pero si lo hace, no lo dejamos).

    Importante: NO capea si LIMIT <= max_rows. Eso sería cambiar la
    intención del usuario. Solo capea cuando excede.

    Casos:
    - "SELECT * FROM t"                  → "SELECT * FROM t LIMIT 1000"
    - "SELECT * FROM t LIMIT 5"            → unchanged
    - "SELECT * FROM t LIMIT 1000"         → unchanged (igual al max)
    - "SELECT * FROM t LIMIT 10000"        → "SELECT * FROM t LIMIT 1000"
    """
    import re
    limit_re = re.compile(r'\bLIMIT\s+(\d+)', re.IGNORECASE)
    match = limit_re.search(query)
    if match is None:
        # No hay LIMIT → agregar
        query_clean = query.rstrip().rstrip(";")
        return f"{query_clean} LIMIT {max_rows}"
    # Hay LIMIT → chequear si excede
    existing = int(match.group(1))
    if existing > max_rows:
        return limit_re.sub(f"LIMIT {max_rows}", query, count=1)
    return query


# ----- Tests rápidos -----
if __name__ == "__main__":
    # Queries válidas
    valid_queries = [
        "SELECT * FROM Customer",
        "SELECT COUNT(*) FROM Customer WHERE Country = 'USA'",
        "WITH top AS (SELECT ArtistId, COUNT(*) as c FROM Album GROUP BY ArtistId) SELECT * FROM top LIMIT 5",
        "EXPLAIN SELECT * FROM Track",
    ]

    # Queries inválidas
    invalid_queries = [
        "DROP TABLE users",
        "DELETE FROM invoices",
        "UPDATE customers SET name = 'foo'",
        "INSERT INTO users VALUES (1, 'hacker')",
        "SELECT * FROM users; DROP TABLE users",
        "SELECT * FROM users WHERE id = 1; -- AND password='admin'",
        "SELECT * FROM users WHERE name = 'foo' UNION SELECT password FROM users",
    ]

    print("✅ Queries válidas:")
    for q in valid_queries:
        valid, err = validate_sql(q)
        status = "✅" if valid else "❌"
        print(f"   {status} {q[:60]}... → {err if not valid else 'OK'}")

    print("\n❌ Queries inválidas (deben ser rechazadas):")
    for q in invalid_queries:
        valid, err = validate_sql(q)
        status = "✅" if not valid else "❌"
        print(f"   {status} {q[:60]}... → {err if not valid else 'OK'}")
