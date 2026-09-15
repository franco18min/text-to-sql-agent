"""
Tests exhaustivos del SQL safety guardrail.

Cobertura:
- Dangerous keywords (DROP, DELETE, UPDATE, INSERT, TRUNCATE, ALTER, CREATE, GRANT, REVOKE, EXEC, EXECUTE, PRAGMA, ATTACH, DETACH, VACUUM, REINDEX, LOAD, SAVEPOINT, ROLLBACK, REPLACE)
- Multi-statement (múltiples `;`)
- Comentarios SQL (`--`, `/* */`)
- Length limit (>2000 chars)
- Valid queries (SELECT, WITH, EXPLAIN, JOIN, subqueries)
- False positives: nombres de columnas que contienen keywords (UPDATED_AT, deleted_at)
- add_limit_if_missing: agrega si falta, no toca si ya hay, CAPA si excede

Correr con:
    pytest tests/test_sql_safety.py -v
"""
import pytest

from app.core.sql_safety import (
    DANGEROUS_KEYWORDS,
    add_limit_if_missing,
    validate_sql,
)


# ============================================================
# Tests de queries que DEBEN ser rechazadas
# ============================================================

class TestDangerousKeywordsRejected:
    """Cada keyword peligrosa debe rechazar la query."""

    @pytest.mark.parametrize("keyword", [
        "DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE",
        "ALTER", "CREATE", "GRANT", "REVOKE", "REPLACE",
        "EXEC", "EXECUTE", "PRAGMA", "ATTACH", "DETACH",
        "VACUUM", "REINDEX", "LOAD", "SAVEPOINT", "ROLLBACK",
    ])
    def test_keyword_at_start_is_rejected(self, keyword):
        sql = f"{keyword} something"
        valid, error = validate_sql(sql)
        assert not valid, f"Query con {keyword} debería ser rechazada"
        assert keyword in error.upper() or "no permit" in error.lower() or "START" in error.upper()

    def test_drop_table_rejected(self):
        """Caso clásico del README: DROP TABLE."""
        valid, error = validate_sql("DROP TABLE users")
        assert not valid
        assert "DROP" in error.upper()

    def test_delete_rejected(self):
        valid, error = validate_sql("DELETE FROM invoices")
        assert not valid

    def test_update_rejected(self):
        valid, error = validate_sql("UPDATE customers SET name = 'foo'")
        assert not valid

    def test_insert_rejected(self):
        valid, error = validate_sql("INSERT INTO users VALUES (1, 'hacker')")
        assert not valid

    def test_truncate_rejected(self):
        valid, error = validate_sql("TRUNCATE TABLE logs")
        assert not valid

    def test_alter_rejected(self):
        valid, error = validate_sql("ALTER TABLE users ADD COLUMN password TEXT")
        assert not valid

    def test_create_rejected(self):
        valid, error = validate_sql("CREATE TABLE evil (x INT)")
        assert not valid

    def test_grant_rejected(self):
        valid, error = validate_sql("GRANT ALL ON users TO public")
        assert not valid

    def test_vacuum_rejected(self):
        """Databricks tiene VACUUM, peligroso para producción."""
        valid, error = validate_sql("VACUUM TABLE customers")
        assert not valid


class TestMultiStatementRejected:
    """Múltiples statements separados por `;` → rechazado."""

    def test_select_then_drop(self):
        """El ejemplo clásico del README."""
        valid, error = validate_sql("SELECT * FROM users; DROP TABLE users")
        assert not valid
        assert "statement" in error.lower() or ";" in error

    def test_select_with_comment_injection(self):
        """Inyección clásica: comentario SQL para esconder el comando."""
        valid, error = validate_sql("SELECT * FROM users WHERE id = 1; -- AND password='admin'")
        # Primero cae por el comentario `--`
        assert not valid
        assert "comentario" in error.lower() or "comment" in error.lower()

    def test_two_selects(self):
        """Dos SELECT separados también son multi-statement."""
        valid, error = validate_sql("SELECT 1; SELECT 2")
        assert not valid

    def test_trailing_semicolon_ok(self):
        """Un solo `;` al final NO es multi-statement (es terminador)."""
        valid, _ = validate_sql("SELECT * FROM users;")
        assert valid


class TestCommentsRejected:
    """Comentarios SQL → rechazado (vector de inyección)."""

    def test_line_comment_rejected(self):
        valid, error = validate_sql("SELECT * FROM users -- get everything")
        assert not valid
        assert "comentario" in error.lower() or "comment" in error.lower()

    def test_block_comment_rejected(self):
        valid, error = validate_sql("SELECT * FROM /* hidden */ users")
        assert not valid

    def test_block_comment_in_middle_rejected(self):
        valid, error = validate_sql("SELECT /* evil */ * FROM users")
        assert not valid


class TestLengthLimit:
    """Queries > 2000 chars → rechazado."""

    def test_very_long_select_rejected(self):
        # Generar query gigante: SELECT * FROM t WHERE col = 'a' OR col = 'b' OR ...
        long_or = " OR ".join([f"col{i} = 'x'" for i in range(200)])
        sql = f"SELECT * FROM t WHERE {long_or}"
        assert len(sql) > 2000
        valid, error = validate_sql(sql)
        assert not valid
        assert "largo" in error.lower() or "2000" in error

    def test_at_limit_accepted(self):
        """Una query de exactamente 2000 chars no se rechaza por longitud."""
        # Construir query de ~2000 chars que empieza con SELECT
        padding = "x" * (2000 - len("SELECT * FROM t WHERE x = '"))
        sql = f"SELECT * FROM t WHERE x = '{padding}"
        assert len(sql) == 2000
        valid, _ = validate_sql(sql)
        # 2000 chars exactos está en el límite, debe pasar
        assert valid


# ============================================================
# Tests de queries que DEBEN ser aceptadas
# ============================================================

class TestValidQueriesAccepted:
    """Queries legítimas read-only → aceptadas."""

    def test_simple_select(self):
        valid, _ = validate_sql("SELECT * FROM users")
        assert valid

    def test_select_with_where(self):
        valid, _ = validate_sql("SELECT name, age FROM users WHERE age > 18")
        assert valid

    def test_select_with_join(self):
        sql = """
        SELECT c.c_name, SUM(l.l_extendedprice) AS total
        FROM samples.tpch.customer c
        JOIN samples.tpch.lineitem l ON c.c_custkey = l.l_orderkey
        GROUP BY c.c_name
        ORDER BY total DESC
        LIMIT 10
        """
        valid, error = validate_sql(sql)
        assert valid, f"JOIN query debería ser válida, error: {error}"

    def test_with_cte(self):
        sql = """
        WITH top_customers AS (
            SELECT c_custkey, SUM(l_extendedprice) AS total
            FROM samples.tpch.lineitem
            GROUP BY c_custkey
            ORDER BY total DESC
            LIMIT 5
        )
        SELECT * FROM top_customers
        """
        valid, error = validate_sql(sql)
        assert valid, f"CTE debería ser válida, error: {error}"

    def test_explain_accepted(self):
        valid, _ = validate_sql("EXPLAIN SELECT * FROM users")
        assert valid

    def test_select_1_accepted(self):
        valid, _ = validate_sql("SELECT 1")
        assert valid

    def test_select_with_functions(self):
        valid, _ = validate_sql("SELECT COUNT(*), AVG(price), MAX(amount) FROM orders")
        assert valid

    def test_select_with_subquery(self):
        sql = """
        SELECT * FROM (SELECT * FROM users WHERE age > 18) AS adults
        WHERE adults.country = 'AR'
        """
        valid, error = validate_sql(sql)
        assert valid, f"Subquery debería ser válida, error: {error}"

    def test_union_accepted(self):
        """UNION no es peligroso per se, lo validamos aparte."""
        valid, _ = validate_sql("SELECT name FROM users UNION SELECT name FROM customers")
        # UNION entre SELECTs legítimos está OK
        # (UNION-based injection se mitiga porque solo se permite SELECT, no DROP/DELETE)
        assert valid

    def test_query_with_string_literal_containing_semicolon(self):
        """Un `;` dentro de un string literal no es multi-statement."""
        valid, _ = validate_sql("SELECT * FROM logs WHERE msg = 'error; ignore'")
        assert valid


class TestFalsePositives:
    """Nombres de columnas que contienen keywords no deben rechazar."""

    def test_updated_at_column_accepted(self):
        """Columna 'updated_at' contiene 'UPDATE' pero es un identifier."""
        valid, error = validate_sql("SELECT updated_at FROM users")
        assert valid, f"updated_at no debería ser rechazado, error: {error}"

    def test_deleted_at_column_accepted(self):
        valid, _ = validate_sql("SELECT deleted_at, name FROM users")
        assert valid

    def test_created_at_column_accepted(self):
        valid, _ = validate_sql("SELECT created_at FROM orders")
        assert valid

    def test_inserted_count_column_accepted(self):
        valid, _ = validate_sql("SELECT inserted_count FROM logs")
        assert valid

    def test_drop_ship_column_accepted(self):
        """Columna 'drop_ship' no debería trigger DROP keyword."""
        valid, _ = validate_sql("SELECT drop_ship FROM orders")
        assert valid


# ============================================================
# Tests de add_limit_if_missing
# ============================================================

class TestAddLimit:
    """Defense in depth: LIMIT nunca debe traer más de max_rows."""

    def test_adds_limit_when_missing(self):
        result = add_limit_if_missing("SELECT * FROM users", max_rows=1000)
        assert "LIMIT 1000" in result.upper()
        assert result == "SELECT * FROM users LIMIT 1000"

    def test_preserves_trailing_semicolon(self):
        result = add_limit_if_missing("SELECT * FROM users;", max_rows=1000)
        assert result == "SELECT * FROM users LIMIT 1000"
        # Sin `;` duplicado
        assert result.count(";") == 0

    def test_keeps_existing_small_limit(self):
        sql = "SELECT * FROM users LIMIT 5"
        result = add_limit_if_missing(sql, max_rows=1000)
        assert result == sql  # unchanged

    def test_keeps_existing_equal_limit(self):
        sql = "SELECT * FROM users LIMIT 1000"
        result = add_limit_if_missing(sql, max_rows=1000)
        assert result == sql  # unchanged, no cape

    def test_caps_excessive_limit(self):
        """EL FIX: LIMIT 10000 → LIMIT 1000."""
        sql = "SELECT * FROM users LIMIT 10000"
        result = add_limit_if_missing(sql, max_rows=1000)
        assert "LIMIT 1000" in result.upper()
        assert "LIMIT 10000" not in result.upper()

    def test_caps_huge_limit(self):
        sql = "SELECT * FROM users LIMIT 9999999"
        result = add_limit_if_missing(sql, max_rows=1000)
        assert "LIMIT 1000" in result.upper()

    def test_caps_case_insensitive(self):
        sql = "SELECT * FROM users limit 5000"
        result = add_limit_if_missing(sql, max_rows=1000)
        assert "LIMIT 1000" in result.upper()
        assert "5000" not in result


# ============================================================
# Tests de integración (casos realistas tpch)
# ============================================================

class TestRealisticTPCQueries:
    """Queries de negocio reales contra samples.tpch."""

    def test_top_customers_query(self):
        sql = """
        SELECT c.c_name, SUM(l.l_extendedprice) AS revenue
        FROM samples.tpch.customer c
        JOIN samples.tpch.lineitem l ON c.c_custkey = l.l_orderkey
        WHERE l.l_shipdate >= '1995-01-01'
        GROUP BY c.c_name
        ORDER BY revenue DESC
        LIMIT 10
        """
        valid, error = validate_sql(sql)
        assert valid, f"Top customers query debería ser válida, error: {error}"

    def test_aggregation_by_nation(self):
        sql = """
        SELECT n.n_name, COUNT(*) AS customer_count, AVG(c.c_acctbal) AS avg_balance
        FROM samples.tpch.customer c
        JOIN samples.tpch.nation n ON c.c_nationkey = n.n_nationkey
        GROUP BY n.n_name
        ORDER BY customer_count DESC
        """
        valid, _ = validate_sql(sql)
        assert valid

    def test_count_query(self):
        sql = "SELECT COUNT(*) FROM samples.tpch.customer WHERE c_nationkey = 21"
        valid, _ = validate_sql(sql)
        assert valid


# ============================================================
# Tests de edge cases
# ============================================================

class TestEdgeCases:
    """Casos borde del validador."""

    def test_empty_string_rejected(self):
        valid, error = validate_sql("")
        assert not valid

    def test_only_whitespace_rejected(self):
        valid, error = validate_sql("   \n\t  ")
        assert not valid

    def test_only_comment_rejected(self):
        valid, _ = validate_sql("-- just a comment")
        assert not valid

    def test_select_lowercase_accepted(self):
        valid, _ = validate_sql("select * from users")
        assert valid

    def test_select_mixed_case_accepted(self):
        valid, _ = validate_sql("Select * From users")
        assert valid

    def test_keyword_set_contains_expected(self):
        """El set de keywords peligrosas incluye lo que esperamos."""
        expected = {"DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE"}
        assert expected.issubset(DANGEROUS_KEYWORDS)
