# Text-to-SQL Agent — UI (Streamlit)

Chat UI que consume el FastAPI backend en `app/main.py`.

## Levantar todo en dev

Necesitás dos terminales desde la raíz del proyecto:

```bash
# Terminal 1: FastAPI backend (puerto 8000)
uvicorn app.main:app --reload --port 8000

# Terminal 2: Streamlit (puerto 8501)
streamlit run ui/streamlit_app.py
```

Después abrí http://localhost:8501.

## Variables de entorno

- `TEXT2SQL_API_URL` (default `http://localhost:8000`): URL del backend.
  Útil si deployás el backend en otro host o detrás de un proxy.

## Features

- Chat con el agente (pregunta en lenguaje natural)
- Visualización del SQL generado (collapsible, con copy)
- Tabla de resultados (pandas `st.dataframe`)
- Chips de metadata: `intent`, `schema_source`, `validation_status`, `rows`, `retries`, `latency_ms`, `model`
- Sidebar: health check del backend, gestión de session, browser del schema
- Multi-turn: la session_id se mantiene entre preguntas para que el agente use memory
- Sin emojis en la UI
