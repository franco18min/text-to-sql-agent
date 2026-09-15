"""
Observability: MLflow tracing wrapper.

Por qué wrapper y no usar `mlflow.start_span()` directo:
- Centraliza config (tracking URI, experiment name)
- Permite mockear en tests
- Loggea latencia automáticamente
- Loggea tokens de Gemini cuando estén disponibles
- **Si MLflow falla a configurar o el SDK de Databricks no está autenticado,
  degrada a no-op silencioso** (la app sigue funcionando).

Por qué MLflow y no LangSmith / LangFuse / custom:
- Databricks lo soporta nativamente (databricks tracking URI)
- Open source, no vendor lock-in
- Se integra con Databricks Free Edition sin costo
- UI incluida en el workspace de Databricks
"""
import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

import mlflow

from app.config import settings


logger = logging.getLogger(__name__)


# Flag global: una vez que detectamos que MLflow no se puede configurar,
# dejamos de intentar (evita logs repetitivos en cada span).
_mlflow_available: bool | None = None


def _is_mlflow_usable() -> bool:
    """
    Devuelve True si MLflow puede abrir spans. Cachea el resultado.
    Si falla la primera vez, devuelve False para siempre en este proceso.
    """
    global _mlflow_available
    if _mlflow_available is not None:
        return _mlflow_available
    try:
        # Probamos abrir un span dummy; si funciona, asumimos que MLflow está OK
        with mlflow.start_span(name="__health_check__"):
            pass
        _mlflow_available = True
    except Exception as e:
        logger.warning("MLflow no usable, traces se ignoran: %s", e)
        _mlflow_available = False
    return _mlflow_available


def configure_mlflow() -> None:
    """
    Configura MLflow al startup. Idempotente.

    Si el tracking URI es "databricks", usa el MLflow server del
    workspace. Si es un HTTP URL custom, usa ese.
    """
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        logger.info("MLflow configurado (tracking_uri=%s)", settings.mlflow_tracking_uri)
    except Exception as e:
        logger.warning("No se pudo configurar MLflow: %s — continuando sin traces", e)
    # Pre-chequeamos si MLflow es usable (cachea el resultado)
    _is_mlflow_usable()


@contextmanager
def start_span(name: str, **attributes: Any) -> Iterator[Any]:
    """
    Context manager que abre un span en MLflow y loggea latencia.

    Si MLflow no se puede usar (Databricks sin autenticar, etc.) degrada
    a un context manager no-op — la app sigue funcionando, solo que sin traces.

    Args:
        name: nombre del span (e.g. "sql_generator_node")
        **attributes: extra metadata (question, sql, model, etc.)

    Usage:
        with start_span("sql_generator", question="top 5 customers"):
            response = generate(prompt)
    """
    start = time.time()
    if not _is_mlflow_usable():
        # No-op span — no rompemos la app si MLflow no está OK
        try:
            yield None
        finally:
            latency_ms = (time.time() - start) * 1000
            # Log local-only para debug
            logger.debug("span[%s] (no-mlflow) latency_ms=%.1f", name, latency_ms)
        return

    # Path normal: MLflow OK
    try:
        with mlflow.start_span(name=name) as span:
            for k, v in attributes.items():
                if isinstance(v, (str, int, float, bool)):
                    try:
                        span.set_attribute(k, v)
                    except Exception:
                        pass
            try:
                yield span
            finally:
                latency_ms = (time.time() - start) * 1000
                mlflow.log_metric(f"{name}.latency_ms", latency_ms)
    except Exception as e:
        # Si MLflow falla a mitad de camino (p.ej. expira token), marcamos
        # como no-usable y degradamos a no-op para no romper el caller
        global _mlflow_available
        logger.warning("MLflow falló durante span %s, desactivando: %s", name, e)
        _mlflow_available = False
        # Re-ejecutamos el cuerpo del span en modo no-op
        try:
            yield None
        finally:
            latency_ms = (time.time() - start) * 1000
            logger.debug("span[%s] (degraded) latency_ms=%.1f", name, latency_ms)


def log_metric(name: str, value: float) -> None:
    """Loggea una métrica al run activo. No-op si MLflow no está usable."""
    if not _is_mlflow_usable():
        return
    try:
        mlflow.log_metric(name, value)
    except Exception:
        pass


def log_param(name: str, value: Any) -> None:
    """Loggea un parámetro. No-op si MLflow no está usable."""
    if not _is_mlflow_usable():
        return
    if not isinstance(value, (str, int, float, bool)):
        value = str(value)
    try:
        mlflow.log_param(name, value)
    except Exception:
        pass