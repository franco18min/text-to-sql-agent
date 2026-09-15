# Interview talking points — Text-to-SQL Agent

Cheatsheet para entrevistas tecnicas. Numeros y respuestas listas.

## Numeros para citar de memoria

- **100% (30/30)** execution accuracy y **100%** execution success (current, `eval_results.json`). Snapshot **historico**: **93.3%** (Q16/Q28 prior a los prompt fixes)
- Tests pytest pasando en ~3s (sin credenciales necesarias gracias a mocks); el count exacto esta en el badge del README
- Latency p50: **25s**, p95: **76s**
- Costo de inferencia: **USD 0** (Gemini free tier + Databricks Free Edition)
- 8 tablas TPC-H con ~6M lineitems
- 10 nodos en el grafo LangGraph, 3 edges condicionales, 1 ciclo de retry por exceptions/errors

---

## Como funciona el agente (pregunta clasica)

> "Es un state machine de LangGraph. Cada nodo hace una cosa: clasifica la intencion (sql_query, chitchat, clarification), inspecciona el schema, genera SQL, lo valida con un guardrail, lo ejecuta, y formatea la respuesta. Hay un ciclo de auto-correccion: si el validador rechaza o el executor falla, vuelve al generador con el error como feedback. Tiene memoria de sesion asi que podes hacer follow-ups referenciando turnos anteriores."

Si te preguntan **por que LangGraph y no LangChain**:

> "LangGraph es state machine explicita. Para auto-correccion necesitás poder modelar 'si falla X, volve a Y con feedback Z' — en LangChain eso es un AgentExecutor con hacks, en LangGraph es nativo. Para prototipos LangChain esta bien, para agentes con logica compleja, LangGraph."

---

## Como evitás que haga dano a la DB (seguridad)

> "Tres capas de defensa en profundidad. Primero, el intent classifier detecta si la pregunta es chitchat o claramente destructiva y se va por esa rama sin generar SQL. Segundo, el SQL validator tiene blocklist de keywords peligrosos (DROP, DELETE, UPDATE, INSERT, etc.) + parseo con sqlparse que rechaza multi-statement + cap de 2000 chars + bloqueo de comentarios SQL + cap de LIMIT a 1000. Tercero, el PAT de Databricks se puede configurar read-only. Esto es defense in depth — si una capa falla, las otras dos te cubren."

Si te preguntan por **SQL injection**:

> "El validator bloquea comentarios SQL (`--` y `/* */`) y rechaza multi-statement. Ademas parsea con sqlparse antes de ejecutar, asi que cualquier intento de meter un `; DROP TABLE` adentro de un string o como comentario queda atrapado."

---

## Que pasa si el SQL generado es incorrecto

> "Dos mecanismos. Primero, dry-run con EXPLAIN antes de ejecutar — si la query no parsea en el warehouse, el validator la rechaza y la regeneracion arranca con el error de EXPLAIN como feedback. Segundo, auto-correccion **solo si hay exception o error** del executor o del validator (resultado vacio es success, no dispara retry). Maximo 3 intentos; despues de eso, el nodo `give_up` explica en lenguaje humano que no pudo resolver la pregunta."

---

## Como medis la calidad (ML engineering culture)

> "Tengo un set de 30 preguntas con ground truth SQL canonico escrito a mano. Lo corro contra el agente y comparo resultados: misma cantidad de filas y misma primera celda (loose match). Tambien mido latencia p50/p95 y retries promedio. Loggeo todo a MLflow cuando hay auth, sino degraded a no-op. Current: **100% (30/30)**. Un snapshot **historico** fue 83% (GTs malos) y despues **93.3%** (Q16/Q28); los prompt fixes subieron el accuracy a 100%."

Si te preguntan por **MLflow**:

> "Es el tracking nativo de Databricks, asi que no necesito otro vendor. Cada nodo abre un span que mide latencia. Cuando el SDK de Databricks no esta autenticado (ej. en CI), degrado a no-op silencioso para que la app siga andando."

---

## Por que Databricks y no Postgres / SQLite

> "Databricks Free Edition viene con `samples.tpch` nativo, que es el benchmark TPC-H estandar. 8 tablas con millones de filas, cualquier data engineer lo conoce. Esto me permite hacer preguntas reales (revenue por nation, top customers, cohortes) sin tener que cargar y mantener una DB local. Ademas, Databricks Unity Catalog + el SDK de Python me da lo mismo que tendria en produccion."

Si te preguntan por **el schema retrieval**:

> "SHOW TABLES + DESCRIBE TABLE. No uso information_schema porque en Free Edition las tablas `samples.*` son legacy de hive_metastore y no aparecen ahi. SHOW TABLES es Spark SQL nativo, ve ambos mundos. Esto es un gotcha real que la mayoria de los agentes pasan por alto."

---

## Que pasa cuando la pregunta es ambigua

> "Tres caminos. Si es claramente chitchat (saludo, pregunta sobre el agente), va al nodo `chitchat` y responde en lenguaje natural sin tocar SQL. Si la pregunta es ambigua pero claramente quiere datos, va al nodo `clarification` que pregunta al usuario que aclare. Si parece una pregunta SQL valida, sigue el pipeline normal."

---

## Que haces con memory / contexto de conversacion

> "Hay un modulo `app/core/memory.py` con dos backends. Para desarrollo: SQLite local en `data/db/sessions.db`. Para produccion: tabla Delta en `samples.tpch.agent_sessions`. El agente guarda el turn del usuario y el del assistant despues de cada pregunta. En el prompt del SQL generator, paso los ultimos 10 turns como contexto. Esto permite hacer preguntas de follow-up referenciando turnos anteriores, tipo 'Y cuantas ordenes pusieron ESOS clientes en 1995?'."

---

## Trade-offs y cosas que no son obvias

**Por que auto-correccion y no un solo intento mas largo?**

> "El auto-correccion te da 'memorias de fallos' — si el LLM recibe el error exacto de Databricks, sabe que columna no existe. Un solo intento largo no tiene ese feedback."

**Por que no stream la respuesta?**

> "El bottleneck es el SQL generation y ejecucion, no el formatter final. Streaming solo del formatter seria 5% del tiempo total. Si lo necesitara, iria a WebSocket."

**Por que no GPT-4 o Claude?**

> "Costo. Gemini free tier da resultados comparables en este dominio. Si fuera produccion, evaluaria GPT-4o-mini por latencia."

**Por que no LangSmith?**

> "MLflow esta nativo en Databricks. LangSmith es bueno pero requiere signup. Mismo feature, menos friccion."

**Que mejorarias con mas tiempo?**

> "Streaming de tokens, autenticacion con OAuth en vez de PAT, eval set mas grande (500+ preguntas), y soporte multi-DB (Snowflake, BigQuery). Tambien un benchmark contra BIRD o Spider para tener una metrica comparable a la industria."

---

## Si te preguntan por que esto importa / por que te importa

> "Vine de Data Engineering y queria hacer el switch a AI Engineering sin perder mi base tecnica. NL2SQL es el punto donde mis dos skills se cruzan: entiendo schemas, query optimization, y data modeling, y al mismo tiempo puedo trabajar con LLMs, prompt engineering, y agent design. Es el tipo de proyecto que demuestra que puedo hacer el puente, no que hice un pivot completo."

---

## Si te piden una demo en vivo

1. Arrancar `make run-api` y `make run-ui` (2 terminales)
2. Abrir http://localhost:8501
3. Hacer 3 preguntas en este orden:
   - "How many customers are in UNITED STATES?" (single-table + JOIN + filter)
   - "Top 5 nations by total order revenue in 1995" (group_by + revenue + 1995)
   - "And how many orders did those customers place in 1995?" (multi-turn con referencia "those")
4. Mostrar el SQL generado (collapsible) y la tabla de resultados
5. Mostrar los chips de metadata: schema_source, validation_status, latency
6. (Opcional) Si la pregunta falla, mostrar como el guardrail la rechaza con un mensaje claro

Demo publica: **TBD** (no hay URL publica live). Correr local en http://localhost:8501. La primera impresion para un recruiter: captura local de la UI o video corto, no un link inventado.
