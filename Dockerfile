FROM python:3.11-slim

WORKDIR /app

# System deps (curl para healthcheck; databricks-sql-connector no necesita más)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps primero (cache de layers)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY ui/ ./ui/
COPY data/ ./data/
COPY env.example .env

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: arranca FastAPI. Para arrancar Streamlit, override con:
#   docker run ... streamlit run ui/streamlit_app.py --server.port 8501
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
