"""
Google Gemini LLM wrapper.

Singleton con retry + dos métodos:
- `generate(prompt)`: texto libre
- `generate_json(prompt)`: objeto JSON parseado (limpia fences ```json```)

Por qué wrapper y no usar el SDK directo en cada nodo:
- Centraliza retry + backoff (Gemini free tier tiene rate limits)
- Centraliza parsing de JSON (Gemini a veces envuelve JSON en markdown)
- Permite mockear fácil en tests (Fase 8)
- Loggea latencia + tokens para MLflow (Fase 6)
"""
import json
import re
import time
from functools import lru_cache
from typing import Any

import google.generativeai as genai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.observability import log_metric, start_span


@lru_cache(maxsize=1)
def get_model():
    """Singleton del modelo Gemini configurado."""
    genai.configure(api_key=settings.google_api_key)
    return genai.GenerativeModel(settings.gemini_model)


def _strip_markdown_json(text: str) -> str:
    """
    Gemini a veces envuelve JSON en fences ```json ... ```.
    Limpia eso para que `json.loads()` funcione.
    """
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _extract_sql_from_response(text: str) -> str:
    """
    Si el LLM devuelve SQL envuelto en markdown ```sql ... ```,
    limpia eso. Si no, devuelve el texto tal cual.
    """
    text = text.strip()
    m = re.search(r"```(?:sql)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


def _extract_usage(response: Any) -> dict:
    """
    Extrae token usage del response de Gemini (si está disponible).
    Retorna dict con input_tokens, output_tokens, total_tokens.
    """
    try:
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return {}
        return {
            "input_tokens": getattr(meta, "prompt_token_count", 0) or 0,
            "output_tokens": getattr(meta, "candidates_token_count", 0) or 0,
            "total_tokens": getattr(meta, "total_token_count", 0) or 0,
        }
    except Exception:
        return {}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def generate(
    prompt: str,
    *,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    span_name: str = "llm.generate",
) -> str:
    """
    Genera texto libre con retry exponencial.

    Args:
        prompt: texto a enviar al LLM.
        temperature: 0.0 = determinístico (default para SQL/code),
            >0 = más creatividad. Para SQL usamos 0.0.
        max_tokens: límite de tokens de salida.
        span_name: nombre del span en MLflow (default "llm.generate";
            los nodos lo override con algo más específico).

    Returns:
        Texto de la respuesta.

    Raises:
        Última excepción si los 3 intentos fallan.
    """
    model = get_model()
    with start_span(span_name, model=settings.gemini_model, temperature=temperature):
        start = time.time()
        # Timeout HTTP de 90s para evitar cuelgues
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
            request_options={"timeout": 90},
        )
        latency_ms = (time.time() - start) * 1000
        log_metric(f"{span_name}.latency_ms", latency_ms)

        usage = _extract_usage(response)
        if usage:
            log_metric(f"{span_name}.input_tokens", usage["input_tokens"])
            log_metric(f"{span_name}.output_tokens", usage["output_tokens"])

        return response.text


def generate_json(
    prompt: str, *, max_tokens: int = 1024, span_name: str = "llm.generate_json"
) -> Any:
    """
    Genera un JSON object. Asume temperature=0 para determinismo.

    Raises:
        ValueError: si la respuesta no es JSON válido después de
            limpiar markdown fences.
    """
    text = generate(prompt, max_tokens=max_tokens, temperature=0.0, span_name=span_name)
    cleaned = _strip_markdown_json(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM no devolvió JSON válido: {cleaned[:200]}... ({e})"
        ) from e


# Helpers públicos para que los nodos los usen sin acoplar a Gemini directamente
def extract_sql(raw_response: str) -> str:
    """Helper público para limpiar SQL de un response del LLM."""
    return _extract_sql_from_response(raw_response)
