"""
Tests del agente con LLM mockeado.

Verifica:
- Clasificación de intención
- Generación de SQL válida (semánticamente, no por ejecución)
- Self-correction cuando hay error
- Routing por intent
- Cap de LIMIT
- Bloqueo de keywords peligrosas

No llama a Gemini ni a Databricks. Rápido (< 3s).
"""
import os
from unittest.mock import patch, MagicMock

import pytest


# ----- Fixtures ---------------------------------------------------------------

@pytest.fixture(autouse=True)
def _ensure_dummy_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy_for_tests")
    monkeypatch.setenv("DATABRICKS_HOST", "dummy.cloud.databricks.com")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dummy")
    monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/dummy")
    monkeypatch.setenv("DATABRICKS_CATALOG", "samples")
    monkeypatch.setenv("DATABRICKS_SCHEMA", "tpch")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-lite-latest")


@pytest.fixture
def mock_db_query():
    """Mock de app.core.db.execute_query para schema introspection y ejecucion."""
    fake_tables = [
        {"database": "tpch", "tableName": "customer", "isTemporary": False},
        {"database": "tpch", "tableName": "nation", "isTemporary": False},
        {"database": "tpch", "tableName": "orders", "isTemporary": False},
        {"database": "tpch", "tableName": "lineitem", "isTemporary": False},
    ]
    fake_columns = [
        {"col_name": "c_custkey", "data_type": "bigint", "comment": None},
        {"col_name": "c_name", "data_type": "string", "comment": None},
        {"col_name": "c_nationkey", "data_type": "bigint", "comment": None},
    ]
    def fake_query(sql, fetch=True, parameters=None):
        if "SHOW TABLES" in sql.upper():
            return fake_tables
        if "DESCRIBE" in sql.upper():
            return fake_columns
        return [{"ok": 1}]
    with patch("app.core.schema.execute_query", side_effect=fake_query), \
         patch("app.core.db.execute_query", side_effect=fake_query):
        yield


# ----- Intent classifier -----------------------------------------------------

class TestIntentClassifier:
    def test_classifies_sql_query(self):
        from app.agent.nodes.intent_classifier import intent_classifier_node
        from app.agent.state import make_initial_state

        fake_response = '{"intent": "sql_query", "confidence": 0.95, "reason": "asking for data"}'
        with patch("app.core.llm.generate", return_value=fake_response):
            state = make_initial_state("How many customers in USA?", "sess_x")
            result = intent_classifier_node(state)
            assert result["intent"] == "sql_query"

    def test_classifies_chitchat(self):
        from app.agent.nodes.intent_classifier import intent_classifier_node
        from app.agent.state import make_initial_state

        fake_response = '{"intent": "chitchat", "confidence": 0.99, "reason": "greeting"}'
        with patch("app.core.llm.generate", return_value=fake_response):
            state = make_initial_state("hola como estas", "sess_x")
            result = intent_classifier_node(state)
            assert result["intent"] == "chitchat"

    def test_classifies_clarification(self):
        from app.agent.nodes.intent_classifier import intent_classifier_node
        from app.agent.state import make_initial_state

        fake_response = '{"intent": "clarification", "confidence": 0.8, "reason": "vague"}'
        with patch("app.core.llm.generate", return_value=fake_response):
            state = make_initial_state("dame los datos", "sess_x")
            result = intent_classifier_node(state)
            assert result["intent"] == "clarification"


# ----- SQL validator ---------------------------------------------------------

class TestSQLValidatorNode:
    def test_valid_sql_passes(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many?", "sess_x")
        state["sql_query"] = "SELECT count(*) FROM samples.tpch.customer LIMIT 1000"
        # Mock EXPLAIN (the validator hits the real DB otherwise)
        with patch("app.agent.nodes.sql_validator.execute_query", return_value=[]):
            result = sql_validator_node(state)
        assert result["sql_valid"] is True
        assert result["validation_error"] == ""

    def test_dangerous_sql_rejected(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("drop it", "sess_x")
        state["sql_query"] = "DROP TABLE samples.tpch.customer"
        # Validation should fail BEFORE hitting DB
        result = sql_validator_node(state)
        assert result["sql_valid"] is False
        assert "DROP" in result["validation_error"].upper() or "peligrosa" in result["validation_error"].lower()

    def test_validation_failure_records_history_and_increments(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("drop it", "sess_x")
        state["sql_query"] = "DROP TABLE samples.tpch.customer"
        result = sql_validator_node(state)
        assert result["retry_count"] == 1
        assert len(result["retry_history"]) == 1
        entry = result["retry_history"][0]
        assert entry["attempt"] == 1
        assert entry["sql"] == "DROP TABLE samples.tpch.customer"
        assert entry["error"]
        assert result["sql_valid"] is False

    def test_validation_failure_appends_existing_history(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("insert it", "sess_x")
        state["sql_query"] = "INSERT INTO samples.tpch.customer VALUES (1)"
        state["retry_count"] = 1
        state["retry_history"] = [
            {"attempt": 1, "sql": "DROP TABLE x", "error": "blocked"},
        ]
        result = sql_validator_node(state)
        assert result["retry_count"] == 2
        assert len(result["retry_history"]) == 2
        assert result["retry_history"][0]["sql"] == "DROP TABLE x"
        assert result["retry_history"][1]["attempt"] == 2
        assert result["retry_history"][1]["sql"] == "INSERT INTO samples.tpch.customer VALUES (1)"
        assert result["retry_history"][1]["error"]

    def test_explain_failure_records_history_and_increments(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many?", "sess_x")
        state["sql_query"] = "SELECT count(*) FROM samples.tpch.customer LIMIT 1000"
        with patch(
            "app.agent.nodes.sql_validator.execute_query",
            side_effect=RuntimeError("warehouse down"),
        ):
            result = sql_validator_node(state)
        assert result["sql_valid"] is False
        assert result["retry_count"] == 1
        assert result["retry_history"][0]["attempt"] == 1
        assert result["retry_history"][0]["sql"] == state["sql_query"]
        assert "warehouse down" in result["retry_history"][0]["error"]

    def test_validation_success_does_not_write_history(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many?", "sess_x")
        state["sql_query"] = "SELECT count(*) FROM samples.tpch.customer LIMIT 1000"
        with patch("app.agent.nodes.sql_validator.execute_query", return_value=[]):
            result = sql_validator_node(state)
        assert result["sql_valid"] is True
        assert "retry_history" not in result
        assert "retry_count" not in result

    def test_limit_added_when_missing(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("?", "sess_x")
        state["sql_query"] = "SELECT * FROM samples.tpch.customer"
        with patch("app.agent.nodes.sql_validator.execute_query", return_value=[]):
            result = sql_validator_node(state)
        # The validator returns the modified SQL in sql_query only if valid; here we check via state
        # The state passed in is mutated by the dict-returned-from-node convention;
        # the actual mutated query lives in add_limit's return which we re-invoke here:
        from app.core.sql_safety import add_limit_if_missing
        assert "LIMIT 1000" in add_limit_if_missing("SELECT * FROM samples.tpch.customer")


class TestSqlExecutionLimit:
    def test_missing_limit_persisted_with_settings_cap(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("?", "sess_limit")
        state["sql_query"] = "SELECT * FROM samples.tpch.customer"
        with patch("app.agent.nodes.sql_validator.settings", create=True) as mock_settings, \
             patch("app.agent.nodes.sql_validator.execute_query", return_value=[]) as mock_explain:
            mock_settings.max_result_rows = 50
            result = sql_validator_node(state)
        assert result["sql_valid"] is True
        assert result["sql_query"] == "SELECT * FROM samples.tpch.customer LIMIT 50"
        mock_explain.assert_called_once_with(
            "EXPLAIN SELECT * FROM samples.tpch.customer LIMIT 50",
            fetch=False,
        )

    def test_oversize_limit_capped_to_max_result_rows(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("?", "sess_limit")
        state["sql_query"] = "SELECT * FROM samples.tpch.orders LIMIT 9999"
        with patch("app.agent.nodes.sql_validator.settings", create=True) as mock_settings, \
             patch("app.agent.nodes.sql_validator.execute_query", return_value=[]):
            mock_settings.max_result_rows = 200
            result = sql_validator_node(state)
        assert result["sql_query"] == "SELECT * FROM samples.tpch.orders LIMIT 200"
        assert "LIMIT 9999" not in result["sql_query"]

    def test_incap_limit_kept_without_extra_limit(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("?", "sess_limit")
        state["sql_query"] = "SELECT n_nationkey FROM samples.tpch.nation LIMIT 7"
        with patch("app.agent.nodes.sql_validator.settings", create=True) as mock_settings, \
             patch("app.agent.nodes.sql_validator.execute_query", return_value=[]):
            mock_settings.max_result_rows = 100
            result = sql_validator_node(state)
        assert result["sql_query"] == "SELECT n_nationkey FROM samples.tpch.nation LIMIT 7"
        assert result["sql_query"].upper().count("LIMIT") == 1

    def test_explain_argument_equals_executed_sql(self):
        from app.agent.nodes.executor import executor_node
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("?", "sess_limit")
        state["sql_query"] = "SELECT * FROM samples.tpch.lineitem"
        with patch("app.agent.nodes.sql_validator.settings", create=True) as v_settings, \
             patch("app.agent.nodes.sql_validator.execute_query", return_value=[]) as mock_explain:
            v_settings.max_result_rows = 25
            validated = sql_validator_node(state)
        state.update(validated)
        explain_sql = mock_explain.call_args[0][0]
        assert explain_sql.startswith("EXPLAIN ")
        persisted = explain_sql[len("EXPLAIN "):]
        assert persisted == validated["sql_query"]
        state["sql_valid"] = True
        with patch("app.agent.nodes.executor.settings", create=True) as e_settings, \
             patch("app.agent.nodes.executor.execute_query", return_value=[{"ok": 1}]) as mock_exec:
            e_settings.max_result_rows = 25
            executed = executor_node(state)
        assert executed["execution_error"] == ""
        mock_exec.assert_called_once_with(persisted)

    def test_executor_recaps_oversize_limit_before_execute(self):
        from app.agent.nodes.executor import executor_node
        from app.agent.state import make_initial_state

        state = make_initial_state("?", "sess_limit")
        state["sql_valid"] = True
        state["sql_query"] = "SELECT * FROM samples.tpch.customer LIMIT 5000"
        with patch("app.agent.nodes.executor.settings", create=True) as mock_settings, \
             patch("app.agent.nodes.executor.execute_query", return_value=[{"ok": 1}]) as mock_exec:
            mock_settings.max_result_rows = 80
            result = executor_node(state)
        assert result["execution_error"] == ""
        mock_exec.assert_called_once_with("SELECT * FROM samples.tpch.customer LIMIT 80")


# ----- Executor --------------------------------------------------------------

class TestExecutorNode:
    def test_execution_failure_records_history_and_increments(self):
        from app.agent.nodes.executor import executor_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many?", "sess_x")
        state["sql_valid"] = True
        state["sql_query"] = "SELECT count(*) FROM samples.tpch.customer LIMIT 1000"
        with patch(
            "app.agent.nodes.executor.execute_query",
            side_effect=RuntimeError("Table not found"),
        ):
            result = executor_node(state)
        assert result["retry_count"] == 1
        assert result["execution_error"]
        assert len(result["retry_history"]) == 1
        entry = result["retry_history"][0]
        assert entry["attempt"] == 1
        assert entry["sql"] == state["sql_query"]
        assert "Table not found" in entry["error"]

    def test_execution_failure_increments_from_existing_count(self):
        from app.agent.nodes.executor import executor_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many?", "sess_x")
        state["sql_valid"] = True
        state["sql_query"] = "SELECT 1 FROM samples.tpch.orders LIMIT 10"
        state["retry_count"] = 2
        state["retry_history"] = [
            {"attempt": 1, "sql": "SELECT bad", "error": "invalid"},
            {"attempt": 2, "sql": "SELECT worse", "error": "invalid"},
        ]
        with patch(
            "app.agent.nodes.executor.execute_query",
            side_effect=RuntimeError("timeout"),
        ):
            result = executor_node(state)
        assert result["retry_count"] == 3
        assert len(result["retry_history"]) == 3
        assert result["retry_history"][2]["attempt"] == 3
        assert result["retry_history"][2]["sql"] == state["sql_query"]
        assert "timeout" in result["retry_history"][2]["error"]

    def test_skip_path_does_not_increment_or_append(self):
        from app.agent.nodes.executor import executor_node
        from app.agent.state import make_initial_state

        state = make_initial_state("drop it", "sess_x")
        state["sql_valid"] = False
        state["sql_query"] = "DROP TABLE samples.tpch.customer"
        state["retry_count"] = 1
        state["retry_history"] = [
            {"attempt": 1, "sql": "DROP TABLE samples.tpch.customer", "error": "blocked"},
        ]
        result = executor_node(state)
        assert result["retry_count"] == 1
        assert "retry_history" not in result
        assert result["execution_error"] == "skipped (validation failed)"

    def test_execution_success_does_not_write_history(self):
        from app.agent.nodes.executor import executor_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many?", "sess_x")
        state["sql_valid"] = True
        state["sql_query"] = "SELECT count(*) FROM samples.tpch.customer LIMIT 1000"
        with patch(
            "app.agent.nodes.executor.execute_query",
            return_value=[{"count(1)": 30127}],
        ):
            result = executor_node(state)
        assert result["execution_error"] == ""
        assert result["execution_result"] == [{"count(1)": 30127}]
        assert result["retry_count"] == 0
        assert "retry_history" not in result


# ----- Schema introspector ---------------------------------------------------

class TestSchemaIntrospector:
    def test_builds_schema_context(self, mock_db_query):
        from app.agent.nodes.schema_introspector import schema_introspector_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many customers in USA?", "sess_x")
        state["intent"] = "sql_query"
        result = schema_introspector_node(state)
        assert result["schema_context"] != ""
        assert any("customer" in t for t in result["schema_table_names"])

    def test_vs_fallback_uses_show_describe(self, mock_db_query):
        from app.agent.nodes.schema_introspector import schema_introspector_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many customers in USA?", "sess_vs")
        with patch("app.agent.nodes.schema_introspector.settings") as mock_settings, \
             patch("app.agent.nodes.schema_introspector.count_tables", return_value=99), \
             patch(
                 "app.core.vector_search.search_similar_schema_chunks",
                 side_effect=RuntimeError("endpoint down"),
             ):
            mock_settings.databricks_catalog = "samples"
            mock_settings.databricks_schema = "tpch"
            mock_settings.databricks_vector_search_endpoint = "vs-ep"
            mock_settings.databricks_vector_search_index = "samples.tpch.idx"
            mock_settings.schema_retrieval_threshold = 20
            result = schema_introspector_node(state)
        assert result["schema_source"] == "show_describe"
        assert "customer" in result["schema_context"].lower() or any(
            "customer" in t for t in result["schema_table_names"]
        )

    def test_vs_fallback_is_not_exception_text(self, mock_db_query):
        from app.agent.nodes.schema_introspector import schema_introspector_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many orders?", "sess_vs2")
        message = "Vector Search unavailable: boom-xyz"
        with patch("app.agent.nodes.schema_introspector.settings") as mock_settings, \
             patch("app.agent.nodes.schema_introspector.count_tables", return_value=50), \
             patch(
                 "app.core.vector_search.search_similar_schema_chunks",
                 side_effect=RuntimeError(message),
             ):
            mock_settings.databricks_catalog = "samples"
            mock_settings.databricks_schema = "tpch"
            mock_settings.databricks_vector_search_endpoint = "vs-ep"
            mock_settings.databricks_vector_search_index = "samples.tpch.idx"
            mock_settings.schema_retrieval_threshold = 10
            result = schema_introspector_node(state)
        assert result["schema_source"] == "show_describe"
        assert message not in result["schema_source"]
        assert "vs_error" not in result["schema_source"]
        assert "boom-xyz" not in result["schema_source"]


# ----- Response formatter ----------------------------------------------------

class TestResponseFormatter:
    def test_explanation_called_with_results(self):
        from app.agent.nodes.response_formatter import response_formatter_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many?", "sess_x")
        state["sql_query"] = "SELECT count(*) FROM samples.tpch.customer LIMIT 1000"
        state["execution_result"] = [{"count(1)": 30127}]
        state["schema_context"] = "customer: c_custkey bigint"
        # Patch at the consumer (the response_formatter imports generate at module level)
        with patch("app.agent.nodes.response_formatter.generate", return_value="Hay 30.127 clientes."):
            result = response_formatter_node(state)
            assert "30.127" in result["final_response"]

    def test_no_results_returns_default_message(self):
        from app.agent.nodes.response_formatter import response_formatter_node
        from app.agent.state import make_initial_state

        state = make_initial_state("?", "sess_x")
        state["sql_query"] = "SELECT count(*) FROM x LIMIT 1000"
        state["execution_result"] = []
        result = response_formatter_node(state)
        # Default message, no LLM call
        assert "no devolvió" in result["final_response"].lower() or "no devuelv" in result["final_response"].lower()


# ----- Schema source typing --------------------------------------------------

class TestSchemaSourceTyping:
    def test_show_describe_is_valid_literal(self):
        from typing import get_args, get_type_hints

        from app.agent.state import AgentState

        allowed = get_args(get_type_hints(AgentState)["schema_source"])
        assert "show_describe" in allowed
        assert set(allowed) == {"show_describe", "cache", "vector_search", "none"}

    def test_free_form_source_rejected(self):
        from typing import get_args, get_type_hints

        from app.agent.state import AgentState

        allowed = get_args(get_type_hints(AgentState)["schema_source"])
        assert "information_schema" not in allowed
        assert "Vector Search unavailable: boom" not in allowed


# ----- Graph routing ---------------------------------------------------------

class TestGraphRouting:
    def test_route_by_intent_sql(self):
        from app.agent.edges import route_by_intent
        assert route_by_intent({"intent": "sql_query"}) == "schema_introspector"

    def test_route_by_intent_chitchat(self):
        from app.agent.edges import route_by_intent
        assert route_by_intent({"intent": "chitchat"}) == "chitchat"

    def test_route_by_intent_clarification(self):
        from app.agent.edges import route_by_intent
        assert route_by_intent({"intent": "clarification"}) == "clarification"

    def test_route_by_validation_valid(self):
        from app.agent.edges import route_by_validation
        assert route_by_validation({
            "sql_valid": True,
            "retry_count": 0,
            "max_retries": 3,
        }) == "executor"

    def test_route_by_validation_invalid_retry(self):
        from app.agent.edges import route_by_validation
        assert route_by_validation({
            "sql_valid": False,
            "retry_count": 1,
            "max_retries": 3,
        }) == "sql_generator"

    def test_route_by_validation_max_retries(self):
        from app.agent.edges import route_by_validation
        assert route_by_validation({
            "sql_valid": False,
            "retry_count": 3,
            "max_retries": 3,
        }) == "give_up"

    def test_route_by_validation_at_custom_max_retries_is_give_up(self):
        from app.agent.edges import route_by_validation

        with patch("app.agent.edges.settings", create=True) as mock_settings:
            mock_settings.max_retries = 2
            assert route_by_validation({
                "sql_valid": False,
                "retry_count": 2,
            }) == "give_up"

    def test_route_by_validation_below_custom_max_retries_retries(self):
        from app.agent.edges import route_by_validation

        with patch("app.agent.edges.settings", create=True) as mock_settings:
            mock_settings.max_retries = 2
            assert route_by_validation({
                "sql_valid": False,
                "retry_count": 1,
            }) == "sql_generator"

    def test_route_by_execution_success(self):
        from app.agent.edges import route_by_execution
        assert route_by_execution({
            "execution_error": "",
            "retry_count": 0,
            "max_retries": 3,
        }) == "response_formatter"

    def test_route_by_execution_error_retry(self):
        from app.agent.edges import route_by_execution
        assert route_by_execution({
            "execution_error": "Table not found",
            "retry_count": 1,
            "max_retries": 3,
        }) == "sql_generator"

    def test_route_by_execution_max_retries(self):
        from app.agent.edges import route_by_execution
        assert route_by_execution({
            "execution_error": "still broken",
            "retry_count": 3,
            "max_retries": 3,
        }) == "give_up"

    def test_route_by_execution_at_custom_max_retries_is_give_up(self):
        from app.agent.edges import route_by_execution

        with patch("app.agent.edges.settings", create=True) as mock_settings:
            mock_settings.max_retries = 1
            assert route_by_execution({
                "execution_error": "timeout",
                "retry_count": 1,
            }) == "give_up"

    def test_route_by_execution_below_custom_max_retries_retries(self):
        from app.agent.edges import route_by_execution

        with patch("app.agent.edges.settings", create=True) as mock_settings:
            mock_settings.max_retries = 4
            assert route_by_execution({
                "execution_error": "timeout",
                "retry_count": 3,
            }) == "sql_generator"

    def test_should_continue_after_retry_still_hardcoded_and_unwired(self):
        import inspect

        from app.agent.edges import should_continue_after_retry
        from app.agent.graph import build_graph

        src = inspect.getsource(should_continue_after_retry)
        assert "settings.max_retries" not in src
        assert ">= 3" in src
        graph_src = inspect.getsource(build_graph)
        assert "should_continue_after_retry" not in graph_src


class TestSuccessLeavesHistoryEmpty:
    def test_validate_and_execute_success_keeps_history_empty(self):
        from app.agent.nodes.executor import executor_node
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many?", "sess_ok")
        state["sql_query"] = "SELECT count(*) FROM samples.tpch.customer LIMIT 1000"
        with patch("app.agent.nodes.sql_validator.execute_query", return_value=[]):
            state.update(sql_validator_node(state))
        state["sql_valid"] = True
        with patch(
            "app.agent.nodes.executor.execute_query",
            return_value=[{"count(1)": 30127}],
        ):
            state.update(executor_node(state))
        assert state["retry_history"] == []
        assert state["retry_count"] == 0
        assert state["execution_result"] == [{"count(1)": 30127}]

    def test_success_does_not_append_when_prior_history_empty_list(self):
        from app.agent.nodes.sql_validator import sql_validator_node
        from app.agent.state import make_initial_state

        state = make_initial_state("How many?", "sess_ok")
        state["sql_query"] = "SELECT n_nationkey FROM samples.tpch.nation LIMIT 5"
        state["retry_history"] = []
        with patch("app.agent.nodes.sql_validator.execute_query", return_value=[]):
            result = sql_validator_node(state)
        assert result["sql_valid"] is True
        assert "retry_history" not in result


class TestRecordRetryFailure:
    def test_first_failure_post_increments_attempt(self):
        from app.agent.retry import record_retry_failure

        out = record_retry_failure({"retry_count": 0, "retry_history": []}, "SELECT 1", "boom")
        assert out["retry_count"] == 1
        assert out["retry_history"] == [{"attempt": 1, "sql": "SELECT 1", "error": "boom"}]

    def test_copies_existing_history(self):
        from app.agent.retry import record_retry_failure

        prior = [{"attempt": 1, "sql": "SELECT bad", "error": "nope"}]
        state = {"retry_count": 1, "retry_history": prior}
        out = record_retry_failure(state, "SELECT 2", "still no")
        assert out["retry_count"] == 2
        assert prior == [{"attempt": 1, "sql": "SELECT bad", "error": "nope"}]
        assert out["retry_history"][1] == {"attempt": 2, "sql": "SELECT 2", "error": "still no"}


class TestCapSqlQuery:
    def test_missing_limit_uses_max_rows(self):
        from app.agent.sql_limit import cap_sql_query

        assert cap_sql_query("SELECT * FROM samples.tpch.customer", 40) == (
            "SELECT * FROM samples.tpch.customer LIMIT 40"
        )

    def test_oversize_limit_is_capped(self):
        from app.agent.sql_limit import cap_sql_query

        assert cap_sql_query("SELECT * FROM t LIMIT 9000", 15) == "SELECT * FROM t LIMIT 15"


class TestAgentRunLatency:
    def test_success_reports_positive_latency_ms(self):
        from app.agent.graph import run_agent

        graph = MagicMock()
        graph.invoke.return_value = {
            "final_response": "Hay 30 clientes.",
            "sql_query": "SELECT count(*) FROM samples.tpch.customer LIMIT 1000",
            "execution_result": [{"count(1)": 30}],
            "execution_error": "",
            "validation_error": "",
            "retry_count": 0,
            "latency_ms": 0.0,
            "intent": "sql_query",
            "schema_source": "show_describe",
        }
        ticks = iter([10.0, 10.04])
        mock_time = MagicMock()
        mock_time.perf_counter.side_effect = lambda: next(ticks)
        with patch("app.agent.graph.build_graph", return_value=graph), \
             patch("app.core.memory.get_history", return_value=[]), \
             patch("app.agent.graph.time", create=True, new=mock_time):
            result = run_agent("How many customers?", "sess_lat_ok")
        assert result["latency_ms"] == pytest.approx(40.0)
        assert result["answer"] == "Hay 30 clientes."
        graph.invoke.assert_called_once()

    def test_give_up_still_reports_positive_latency_ms(self):
        from app.agent.graph import run_agent

        graph = MagicMock()
        graph.invoke.return_value = {
            "final_response": "No pude generar SQL válido después de 2 intentos.",
            "sql_query": "DROP TABLE samples.tpch.customer",
            "execution_result": [],
            "execution_error": "",
            "validation_error": "blocked",
            "retry_count": 2,
            "latency_ms": 0.0,
            "intent": "sql_query",
            "schema_source": "show_describe",
        }
        ticks = iter([5.0, 5.012])
        mock_time = MagicMock()
        mock_time.perf_counter.side_effect = lambda: next(ticks)
        with patch("app.agent.graph.build_graph", return_value=graph), \
             patch("app.core.memory.get_history", return_value=[]), \
             patch("app.agent.graph.time", create=True, new=mock_time):
            result = run_agent("borra todo", "sess_lat_fail")
        assert result["latency_ms"] == pytest.approx(12.0)
        assert result["retry_count"] == 2
        assert result["error"] == "blocked"


class TestCustomMaxRetriesLoop:
    def test_give_up_after_two_invalid_generations(self, mock_db_query):
        from app.agent.graph import run_agent

        with patch(
            "app.agent.nodes.intent_classifier.generate_json",
            return_value={"intent": "sql_query", "confidence": 0.95, "reason": "asking for data"},
        ), \
             patch("app.agent.nodes.sql_generator.generate", return_value="DROP TABLE samples.tpch.customer"), \
             patch("app.core.memory.get_history", return_value=[]), \
             patch("app.core.memory.save_turn"), \
             patch("app.agent.edges.settings", create=True) as mock_settings:
            mock_settings.max_retries = 2
            result = run_agent("borra todo", "sess_retry")
        assert result["retry_count"] == 2
        assert result["error"]
        assert "2 intentos" in result["answer"]
