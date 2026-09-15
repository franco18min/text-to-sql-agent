"""
Text-to-SQL Agent — Streamlit chat UI.

Comunica con el FastAPI backend en `app.main:app` (puerto 8000 por default).
Para arrancar todo en dev:

    # Terminal 1
    uvicorn app.main:app --reload --port 8000

    # Terminal 2
    streamlit run ui/streamlit_app.py

Sin emojis por preferencia del usuario (Franco) — "es muy de ia generativa".
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st


# ============================================================
# Config
# ============================================================
API_BASE = os.environ.get("TEXT2SQL_API_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 120  # el agente puede tardar 30-60s con retries


st.set_page_config(
    page_title="Text-to-SQL Agent",
    page_icon=None,  # sin favicon con emoji
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Custom CSS — dark, sin emojis
# ============================================================
st.markdown(
    """
    <style>
        .block-container { padding-top: 1.5rem; }
        .meta-chip {
            display: inline-block;
            padding: 2px 8px;
            margin: 2px 4px 2px 0;
            border-radius: 6px;
            font-size: 0.75rem;
            font-family: monospace;
            background: #262730;
            color: #fafafa;
            border: 1px solid #3a3a4a;
        }
        .meta-chip.error { background: #5a1f1f; border-color: #7a2f2f; color: #fdd; }
        .meta-chip.warn  { background: #4a3a1f; border-color: #7a6a2f; color: #ffd; }
        .meta-chip.ok    { background: #1f3a2f; border-color: #2f6a4f; color: #dfd; }
        .sql-box {
            background: #0e1117;
            border: 1px solid #2a2a3a;
            border-radius: 6px;
            padding: 0.6rem 0.8rem;
            font-family: 'SF Mono', Consolas, monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            word-break: break-word;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# API client
# ============================================================
class APIClient:
    """Wrapper chiquito sobre requests, con manejo de errores claro."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def health(self, deep: bool = False) -> dict[str, Any]:
        r = requests.get(self._url("/health"), params={"deep": deep}, timeout=90)
        r.raise_for_status()
        return r.json()

    def schema(self) -> dict[str, Any]:
        r = requests.get(self._url("/schema"), timeout=30)
        r.raise_for_status()
        return r.json()

    def query(
        self,
        question: str,
        session_id: str | None = None,
        include_sql: bool = True,
        include_results: bool = True,
        max_rows: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "question": question,
            "include_sql": include_sql,
            "include_results": include_results,
        }
        if session_id:
            payload["session_id"] = session_id
        if max_rows is not None:
            payload["max_rows"] = max_rows
        r = requests.post(self._url("/query"), json=payload, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return r.json()

    def list_sessions(self, limit: int = 20) -> dict[str, Any]:
        r = requests.get(self._url("/sessions"), params={"limit": limit}, timeout=10)
        r.raise_for_status()
        return r.json()

    def new_session(self) -> dict[str, Any]:
        r = requests.post(self._url("/sessions"), timeout=10)
        r.raise_for_status()
        return r.json()

    def get_session(self, session_id: str) -> dict[str, Any]:
        r = requests.get(self._url(f"/sessions/{session_id}"), timeout=10)
        r.raise_for_status()
        return r.json()

    def delete_session(self, session_id: str) -> dict[str, Any]:
        r = requests.delete(self._url(f"/sessions/{session_id}"), timeout=10)
        r.raise_for_status()
        return r.json()


@st.cache_resource(show_spinner=False)
def get_client(base_url: str) -> APIClient:
    return APIClient(base_url)


client = get_client(API_BASE)


# ============================================================
# Session state init
# ============================================================
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []  # lista de dicts {role, content, metadata?}
if "last_error" not in st.session_state:
    st.session_state.last_error = None


# ============================================================
# Sidebar — backend status, sesión, schema
# ============================================================
with st.sidebar:
    st.markdown("### Text-to-SQL Agent")
    st.caption(f"API: `{API_BASE}`")

    st.divider()

    # Backend health
    st.markdown("**Backend status**")
    if st.button("Ping backend", use_container_width=True):
        try:
            with st.spinner("Pinging Databricks + LLM..."):
                h = client.health(deep=True)
            st.session_state.last_error = None
            status_chip = "ok" if h.get("status") == "ok" else ("warn" if h.get("status") == "degraded" else "error")
            st.markdown(
                f'<span class="meta-chip {status_chip}">status: {h.get("status")}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<span class="meta-chip">model: {h.get("model")}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<span class="meta-chip">memory: {h.get("memory_backend")}</span>',
                unsafe_allow_html=True,
            )
            db_ok = h.get("databricks_reachable")
            llm_ok = h.get("llm_reachable")
            if db_ok is not None:
                st.markdown(
                    f'<span class="meta-chip {"ok" if db_ok else "error"}">databricks: {"OK" if db_ok else "FAIL"}</span>',
                    unsafe_allow_html=True,
                )
            if llm_ok is not None:
                st.markdown(
                    f'<span class="meta-chip {"ok" if llm_ok else "error"}">llm: {"OK" if llm_ok else "FAIL"}</span>',
                    unsafe_allow_html=True,
                )
            if h.get("detail"):
                st.caption(h["detail"])
        except Exception as e:
            st.session_state.last_error = f"Backend no alcanzable: {e}"
            st.markdown(
                f'<span class="meta-chip error">backend DOWN</span>',
                unsafe_allow_html=True,
            )
            st.caption(st.session_state.last_error)
    else:
        # Light health (sin ping profundo)
        try:
            h = client.health(deep=False)
            db = h.get("databricks_configured")
            st.markdown(
                f'<span class="meta-chip {"ok" if db else "warn"}">config: {"ready" if db else "missing env"}</span>',
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.markdown(
                f'<span class="meta-chip error">backend DOWN</span>',
                unsafe_allow_html=True,
            )
            st.caption(str(e))

    st.divider()

    # Session management
    st.markdown("**Session**")
    if st.session_state.session_id:
        st.code(st.session_state.session_id, language=None)
    else:
        st.caption("(no session)")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("New session", use_container_width=True):
            try:
                s = client.new_session()
                st.session_state.session_id = s["session_id"]
                st.session_state.messages = []
                st.rerun()
            except Exception as e:
                st.error(f"No pude crear session: {e}")
    with col2:
        if st.button("Clear chat", use_container_width=True) and st.session_state.session_id:
            st.session_state.messages = []

    st.divider()

    # Schema browser (collapsible)
    with st.expander("Database schema", expanded=False):
        if st.button("Load schema", use_container_width=True, key="load_schema"):
            try:
                with st.spinner("Loading schema..."):
                    sch = client.schema()
                st.session_state._schema = sch
            except Exception as e:
                st.error(str(e))
        sch = st.session_state.get("_schema")
        if sch:
            st.caption(f"{sch.get('total_tables', 0)} tables in `{sch.get('catalog')}.{sch.get('schema')}`")
            for t in sch.get("tables", []):
                st.markdown(f"**`{t['table']}`**")
                for col in t.get("columns", []):
                    nullable = "NULL" if col.get("nullable", True) else "NOT NULL"
                    st.markdown(
                        f"- `{col.get('name')}` *({col.get('type')}, {nullable})*"
                    )

    st.divider()
    st.caption("Stack: Databricks + LangGraph + Gemini")


# ============================================================
# Header
# ============================================================
st.title("Text-to-SQL Agent")
st.caption(
    "Hacé una pregunta en lenguaje natural sobre la base `samples.tpch`. "
    "El agente la traduce a SQL, valida con un guardrail, la ejecuta contra Databricks "
    "y devuelve la respuesta + resultados + trace de MLflow."
)


# ============================================================
# Chat history rendering
# ============================================================
def render_assistant_message(meta: dict[str, Any]) -> None:
    """Renderiza un mensaje del asistente con todos los chips de metadata."""
    # SQL
    sql = meta.get("sql_query")
    if sql:
        with st.expander("SQL generado", expanded=False):
            st.code(sql, language="sql")

    # Tabla de resultados
    results = meta.get("results") or []
    if results:
        df = pd.DataFrame(results)
        st.markdown("**Resultados**")
        st.dataframe(df, use_container_width=True, hide_index=True)
    elif meta.get("intent") == "sql_query" and not meta.get("error"):
        st.caption("(La query no devolvió filas)")

    # Chips de metadata
    chips: list[tuple[str, str]] = []  # (clase_css, contenido)
    if meta.get("intent"):
        chips.append(("", f"intent: {meta['intent']}"))
    if meta.get("schema_source"):
        cls = "ok" if meta["schema_source"] == "vector_search" else ""
        chips.append((cls, f"schema: {meta['schema_source']}"))
    if meta.get("validation_status"):
        cls = "ok" if meta["validation_status"] == "valid" else ("error" if meta["validation_status"] == "invalid" else "")
        chips.append((cls, f"validation: {meta['validation_status']}"))
    chips.append(("", f"rows: {meta.get('rows_returned', 0)}"))
    if meta.get("retry_count", 0) > 0:
        chips.append(("warn", f"retries: {meta['retry_count']}"))
    if meta.get("latency_ms"):
        chips.append(("", f"{meta['latency_ms']:.0f} ms"))
    if meta.get("model_used"):
        chips.append(("", f"model: {meta['model_used']}"))

    if chips:
        html = " ".join(
            f'<span class="meta-chip {cls}">{content}</span>'
            for cls, content in chips
        )
        st.markdown(html, unsafe_allow_html=True)

    # Error
    if meta.get("error"):
        st.markdown(
            f'<span class="meta-chip error">error: {meta["error"][:200]}</span>',
            unsafe_allow_html=True,
        )


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("meta"):
            render_assistant_message(msg["meta"])


# ============================================================
# Input + dispatch
# ============================================================
prompt = st.chat_input("Escribí tu pregunta sobre los datos...")

if prompt:
    # Asegurar session_id
    if not st.session_state.session_id:
        try:
            s = client.new_session()
            st.session_state.session_id = s["session_id"]
        except Exception as e:
            st.error(f"No pude crear session: {e}")
            st.stop()

    # Render del user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Llamada al backend
    with st.chat_message("assistant"):
        with st.spinner("Pensando... (Databricks + Gemini)"):
            try:
                resp = client.query(
                    question=prompt,
                    session_id=st.session_state.session_id,
                )
                answer = resp.get("answer", "")
                st.markdown(answer if answer else "_(sin respuesta)_")
                render_assistant_message(resp)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer or "_(sin respuesta)_",
                    "meta": resp,
                })
            except requests.HTTPError as e:
                err = f"Error HTTP {e.response.status_code}: {e.response.text[:300]}"
                st.error(err)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {err}",
                    "meta": {"error": err, "intent": "give_up"},
                })
            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                st.error(err)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {err}",
                    "meta": {"error": err, "intent": "give_up"},
                })
