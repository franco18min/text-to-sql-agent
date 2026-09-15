"""
chitchat: nodo terminal para preguntas que no son de SQL.

Responde brevemente sin tocar DB ni SQL. Por ahora el LLM responde libre
sin prompt específico (se puede mejorar con un system prompt más adelante).
"""
from app.core.llm import generate
from app.agent.state import AgentState


def chitchat_node(state: AgentState) -> dict:
    prompt = (
        "Sos el agente Text-to-SQL de un proyecto de portfolio. "
        "Respondé brevemente en español a este mensaje del usuario. "
        "Si te preguntan qué podés hacer, mencioná que podés responder "
        "preguntas de negocio sobre samples.tpch (clientes, órdenes, "
        "partes, proveedores, etc.) y que corres queries contra Databricks. "
        "No inventes que podés hacer otras cosas.\n\n"
        f"Usuario: {state['question']}\nAsistente:"
    )
    text = generate(prompt, temperature=0.3, max_tokens=512)
    return {"final_response": text}
