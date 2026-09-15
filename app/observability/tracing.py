"""
MLflow tracing initialization.

Centraliza la config de MLflow al startup de la app.
"""
from app.observability import configure_mlflow


def init_tracing() -> None:
    """Inicializa MLflow. Llamar una vez al startup de la API."""
    configure_mlflow()
