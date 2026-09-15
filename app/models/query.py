"""
Request schemas para la API.
"""
from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Body del POST /query"""

    question: str = Field(..., min_length=3, max_length=2000, description="Pregunta en lenguaje natural")
    session_id: Optional[str] = Field(default=None, description="ID de sesión para memoria multi-turn")
    include_sql: bool = Field(default=True, description="Devolver la query SQL generada")
    include_results: bool = Field(default=True, description="Devolver las filas de resultado")
    max_rows: Optional[int] = Field(default=None, ge=1, le=1000, description="Override de MAX_RESULT_ROWS")
