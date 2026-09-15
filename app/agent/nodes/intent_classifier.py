"""
intent_classifier: primer nodo del agente.

Clasifica la pregunta del usuario en:
- "sql_query": quiere datos → continuar con el pipeline normal
- "chitchat": saludo/pregunta sobre el agente → responder y terminar
- "clarification": pregunta ambigua → pedir reformulación

Devuelve un dict parcial con `intent` que se mergea con el state.
"""
from app.agent.prompts import INTENT_CLASSIFIER_PROMPT
from app.core.llm import generate_json
from app.agent.state import AgentState


def intent_classifier_node(state: AgentState) -> dict:
    question = state["question"]
    prompt = INTENT_CLASSIFIER_PROMPT.format(question=question)
    result = generate_json(prompt, max_tokens=256)
    intent = result.get("intent", "sql_query")
    # Default defensivo: si el LLM devuelve algo raro, tratar como sql_query
    if intent not in ("sql_query", "chitchat", "clarification"):
        intent = "sql_query"
    return {"intent": intent}
