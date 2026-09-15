"""
Tests de los endpoints de FastAPI.

Usa FastAPI TestClient con LLM y DB mockeados (no requiere credenciales reales).
Rápido (< 5s total) para CI.
"""
import os
from unittest.mock import patch, MagicMock

import pytest
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient


# ----- Fixtures ---------------------------------------------------------------

@pytest.fixture(autouse=True)
def _ensure_dummy_env(monkeypatch):
    """Set dummy env vars so Settings can load without real secrets."""
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy_for_tests")
    monkeypatch.setenv("DATABRICKS_HOST", "dummy.cloud.databricks.com")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dummy")
    monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/dummy")
    monkeypatch.setenv("DATABRICKS_CATALOG", "samples")
    monkeypatch.setenv("DATABRICKS_SCHEMA", "tpch")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-lite-latest")


@pytest.fixture
def mock_run_agent():
    """Mock de _run_agent_or_503 (la función que el endpoint llama, con lazy import)."""
    fake_result = {
        "answer": "Hay 30.127 clientes en USA.",
        "sql_query": "SELECT count(*) FROM samples.tpch.customer c JOIN samples.tpch.nation n ON c.c_nationkey = n.n_nationkey WHERE n.n_name = 'UNITED STATES' LIMIT 1000",
        "results": [{"count(1)": 30127}],
        "error": None,
        "retry_count": 0,
        "latency_ms": 25000.0,
        "session_id": "sess_test123",
        "intent": "sql_query",
        "schema_source": "show_describe",
        "schema_table_names": ["customer", "nation"],
        "trace_url": None,
    }
    with patch("app.api.chat._run_agent_or_503", return_value=fake_result) as mock:
        yield mock


@pytest.fixture
def mock_db_health():
    """Mock de los helpers de health (que internamente hacen lazy import de execute_query)."""
    with patch("app.api.health._ping_databricks", return_value=(True, None)):
        yield


@pytest.fixture
def mock_llm_health():
    """Mock del ping al LLM para /health?deep=true."""
    with patch("app.api.health._ping_llm", return_value=(True, None)):
        yield


@pytest.fixture
def client(mock_run_agent, mock_db_health, mock_llm_health):
    """TestClient con TODO mockeado (no llama a Databricks ni a Gemini).

    Usamos TestClient sin context manager para evitar correr el lifespan,
    que intenta inicializar MLflow y puede colgarse en CI.
    """
    from app.main import app
    c = TestClient(app)
    yield c
    c.close()


# ----- /health ---------------------------------------------------------------

class TestHealth:
    def test_shallow_health(self, client):
        """GET /health sin deep=true: solo verifica env vars."""
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("ok", "degraded")
        assert body["model"] == "gemini-flash-lite-latest"
        assert body["databricks_configured"] is True
        assert body["memory_backend"] in ("in_memory", "delta")
        assert body["version"] == "1.0.0"

    def test_deep_health(self, client):
        """GET /health?deep=true: pingea DB + LLM (mockeados)."""
        r = client.get("/health", params={"deep": True, "skip_llm": False})
        assert r.status_code == 200
        body = r.json()
        assert body["databricks_reachable"] is True
        assert body["llm_reachable"] is True
        assert body["status"] == "ok"

    def test_deep_health_skip_llm(self, client):
        """GET /health?deep=true&skip_llm=true: solo pingea DB."""
        r = client.get("/health", params={"deep": True, "skip_llm": True})
        assert r.status_code == 200
        body = r.json()
        assert body["databricks_reachable"] is True
        assert body["llm_reachable"] is None


# ----- /query ----------------------------------------------------------------

class TestQuery:
    def test_valid_query_returns_200(self, client, mock_run_agent):
        """POST /query con payload válido -> 200 + AgentResponse completo."""
        r = client.post("/query", json={
            "question": "How many customers are in UNITED STATES?",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["answer"] == "Hay 30.127 clientes en USA."
        assert "samples.tpch.customer" in body["sql_query"]
        assert body["intent"] == "sql_query"
        assert body["validation_status"] == "valid"  # no error => valid
        assert body["rows_returned"] == 1
        assert body["retry_count"] == 0
        # session_id se genera si el caller no manda uno
        assert body["session_id"].startswith("sess_")

    def test_existing_session_id_is_preserved(self, client, mock_run_agent):
        """POST /query con session_id -> se respeta el que mandó el cliente."""
        r = client.post("/query", json={
            "question": "How many?",
            "session_id": "sess_myown",
        })
        assert r.status_code == 200
        assert r.json()["session_id"] == "sess_myown"

    def test_question_too_short_rejected(self, client):
        """Pregunta < 3 chars -> 422 (Pydantic min_length=3)."""
        r = client.post("/query", json={"question": "ab"})
        assert r.status_code == 422

    def test_question_too_long_rejected(self, client):
        """Pregunta > 2000 chars -> 422."""
        r = client.post("/query", json={"question": "x" * 2001})
        assert r.status_code == 422

    def test_include_sql_false_strips_sql(self, client, mock_run_agent):
        """include_sql=false -> sql_query es None en la respuesta."""
        r = client.post("/query", json={
            "question": "How many?",
            "include_sql": False,
        })
        assert r.status_code == 200
        assert r.json()["sql_query"] is None

    def test_include_results_false_strips_rows(self, client, mock_run_agent):
        """include_results=false -> results=[] y rows_returned=0."""
        r = client.post("/query", json={
            "question": "How many?",
            "include_results": False,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["results"] == []
        assert body["rows_returned"] == 0

    def test_max_rows_caps_results(self, client):
        """max_rows=2 -> results tiene a lo sumo 2 filas."""
        fake_result = {
            "answer": "...",
            "sql_query": "SELECT 1",
            "results": [{"a": 1}, {"a": 2}, {"a": 3}, {"a": 4}],
            "error": None,
            "retry_count": 0,
            "latency_ms": 1.0,
            "session_id": "sess_x",
            "intent": "sql_query",
            "schema_source": "show_describe",
            "schema_table_names": [],
        }
        with patch("app.api.chat._run_agent_or_503", return_value=fake_result):
            r = client.post("/query", json={"question": "test question", "max_rows": 2})
        assert r.status_code == 200
        assert len(r.json()["results"]) == 2


# ----- /sessions -------------------------------------------------------------

class TestSessions:
    def test_create_session(self, client):
        """POST /sessions -> crea y devuelve session_id nuevo."""
        r = client.post("/sessions")
        assert r.status_code == 201
        body = r.json()
        assert body["action"] == "created"
        assert body["session_id"].startswith("sess_")

    def test_list_sessions(self, client):
        """GET /sessions -> devuelve estructura con total + sessions."""
        r = client.get("/sessions")
        assert r.status_code == 200
        body = r.json()
        assert "sessions" in body
        assert "total" in body
        assert isinstance(body["sessions"], list)

    def test_get_session(self, client):
        """GET /sessions/{id} -> devuelve history (puede estar vacia)."""
        r = client.get("/sessions/sess_doesnotexist")
        assert r.status_code == 200
        body = r.json()
        assert body["session_id"] == "sess_doesnotexist"
        assert body["turn_count"] == 0
        assert body["history"] == []

    def test_delete_session(self, client):
        """DELETE /sessions/{id} -> 200 + cleared."""
        r = client.delete("/sessions/sess_doesnotexist")
        assert r.status_code == 200
        body = r.json()
        assert body["action"] == "cleared"


def test_app_package_version_is_1_0_0():
    from app import __version__

    assert __version__ == "1.0.0"


# ----- / ---------------------------------------------------------------------

class TestRoot:
    def test_root_lists_endpoints(self, client):
        """GET / -> devuelve service + endpoints list."""
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["service"] == "text-to-sql-agent"
        assert body["version"] == "1.0.0"
        assert "POST /query" in body["endpoints"]
        assert "GET  /health" in body["endpoints"]


# ----- /schema ---------------------------------------------------------------

class TestSchema:
    def test_get_schema_maps_catalog_and_full_name(self, client):
        """GET /schema: catalog/schema/bare table + full_name from settings + list_tables."""
        spark_cols = [
            {"col_name": "c_custkey", "data_type": "bigint", "nullable": False, "comment": "pk"},
        ]
        with patch("app.core.schema.list_tables", return_value=["customer"]) as mock_list, patch(
            "app.core.schema.describe_table", return_value=spark_cols
        ) as mock_describe:
            r = client.get("/schema")
        assert r.status_code == 200
        body = r.json()
        assert body["catalog"] == "samples"
        assert body["schema"] == "tpch"
        assert body["total_tables"] == 1
        table = body["tables"][0]
        assert table["catalog"] == "samples"
        assert table["schema"] == "tpch"
        assert table["table"] == "customer"
        assert table["full_name"] == "samples.tpch.customer"
        mock_list.assert_called_once_with("samples", "tpch")
        mock_describe.assert_called_once_with("samples", "tpch", "customer")

    def test_get_schema_maps_spark_columns_to_http_keys(self, client):
        """Spark col_name/data_type/nullable/comment -> HTTP name/type/nullable/comment."""
        spark_cols = [
            {"col_name": "c_name", "data_type": "string", "nullable": True, "comment": "customer name"},
            {"col_name": "c_acctbal", "data_type": "double", "nullable": False},
        ]
        with patch("app.core.schema.list_tables", return_value=["customer"]), patch(
            "app.core.schema.describe_table", return_value=spark_cols
        ):
            r = client.get("/schema")
        assert r.status_code == 200
        cols = r.json()["tables"][0]["columns"]
        assert cols[0]["name"] == "c_name"
        assert cols[0]["type"] == "string"
        assert cols[0]["nullable"] is True
        assert cols[0]["comment"] == "customer name"
        assert cols[1]["name"] == "c_acctbal"
        assert cols[1]["type"] == "double"
        assert cols[1]["nullable"] is False
        assert cols[1]["comment"] == ""

    def test_get_schema_listing_failure_returns_empty_200(self, client):
        """list_tables raising -> 200 and tables=[]."""
        with patch("app.core.schema.list_tables", side_effect=RuntimeError("warehouse down")):
            r = client.get("/schema")
        assert r.status_code == 200
        body = r.json()
        assert body["tables"] == []
        assert body["total_tables"] == 0
        assert body["catalog"] == "samples"
        assert body["schema"] == "tpch"


# ----- CORS ------------------------------------------------------------------

class TestCorsOrigins:
    def test_streamlit_cloud_origin_allowed(self, client):
        r = client.get("/health", headers={"Origin": "https://foo.streamlit.app"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "https://foo.streamlit.app"

    def test_hf_space_origin_allowed(self, client):
        r = client.get("/health", headers={"Origin": "https://bar.hf.space"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "https://bar.hf.space"

    def test_localhost_streamlit_origin_allowed(self, client):
        r = client.get("/health", headers={"Origin": "http://localhost:8501"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://localhost:8501"

    def test_loopback_streamlit_origin_allowed(self, client):
        r = client.get("/health", headers={"Origin": "http://127.0.0.1:8501"})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:8501"

    def test_cors_config_does_not_use_glob_origin_strings(self):
        from app.main import app

        cors = next(m for m in app.user_middleware if m.cls is CORSMiddleware)
        origins = cors.kwargs.get("allow_origins") or []
        assert "https://*.streamlit.app" not in origins
        assert "https://*.hf.space" not in origins
        regex = cors.kwargs.get("allow_origin_regex") or ""
        assert r"https://.*\.(streamlit\.app|hf\.space)" == regex
        assert "http://localhost:8501" in origins
        assert "http://127.0.0.1:8501" in origins
        assert cors.kwargs.get("allow_credentials") is True
