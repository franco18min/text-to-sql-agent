"""
Centralized config (Pydantic Settings).

Lee .env una sola vez y expone `settings` como singleton.
Todas las vars del sistema se acceden via `settings.<var>`.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- Google Gemini -----
    google_api_key: str = Field(default="", description="https://aistudio.google.com/app/apikey")
    gemini_model: str = Field(default="gemini-flash-lite-latest", description="Modelo de Gemini a usar")
    gemini_embedding_model: str = Field(
        default="text-embedding-004",
        description="Modelo de embeddings para Vector Search (opcional)",
    )

    # ----- Databricks -----
    databricks_host: str = Field(default="", description="https://<workspace>.databricks.com")
    databricks_token: str = Field(default="", description="Personal Access Token")
    databricks_http_path: str = Field(
        default="",
        description="SQL Warehouse HTTP Path (/sql/1.0/warehouses/<id>)",
    )
    databricks_catalog: str = Field(default="samples", description="UC catalog target")
    databricks_schema: str = Field(default="tpch", description="UC schema target (samples.tpch)")

    # ----- Databricks Vector Search (Fase 3) -----
    databricks_vector_search_endpoint: str = Field(
        default="",
        description="Nombre del endpoint de Vector Search (ej: 'text2sql-schema-endpoint')",
    )
    databricks_vector_search_index: str = Field(
        default="",
        description="Nombre completo del índice (catalog.schema.index_name)",
    )

    # ----- Agent behavior -----
    max_retries: int = Field(default=3, ge=0, le=10)
    max_query_length: int = Field(default=2000, ge=100, le=10000)
    max_result_rows: int = Field(default=1000, ge=10, le=10000)
    query_timeout_seconds: int = Field(default=30, ge=5, le=120)
    schema_retrieval_threshold: int = Field(
        default=20,
        description="Si el schema tiene menos de N tablas, usar information_schema directo. Si tiene más, usar Vector Search.",
    )

    # ----- Memory -----
    memory_type: Literal["in_memory", "delta"] = Field(
        default="in_memory",
        description="Backend de session memory",
    )
    session_timeout_minutes: int = Field(default=30, ge=1, le=1440)

    # ----- MLflow (Fase 6) -----
    mlflow_tracking_uri: str = Field(
        default="databricks",
        description="'databricks' usa el tracking server del workspace; o una URL http://...",
    )
    mlflow_experiment_name: str = Field(default="/Users/<tu-email>/text2sql-agent")

    # ----- API -----
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = Field(default="INFO")

    # ----- Derived helpers -----
    @property
    def fqdn_target_table(self) -> str:
        """Shortcut para el schema target completo: samples.tpch"""
        return f"{self.databricks_catalog}.{self.databricks_schema}"

    @property
    def is_databricks_configured(self) -> bool:
        """True si las vars mínimas de Databricks están presentes."""
        return bool(
            self.databricks_host
            and self.databricks_token
            and self.databricks_http_path
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton de Settings. Usar siempre `get_settings()` o `settings`."""
    return Settings()


# Conveniencia: `from app.config import settings`
settings = get_settings()
