# Resultados detallados de la evaluacion

## Setup

- **30 preguntas** sobre `samples.tpch` (8 tablas TPC-H: region, nation, customer, orders, lineitem, supplier, part, partsupp)
- **Categorias**: single_table_aggregate, single_table_filter, two_table_join, three_table_join, group_by_order, having_subquery, edge_case
- **Dificultad**: easy, medium, hard
- **Modelo**: `gemini-flash-lite-latest` (Gemini free tier)
- **DB**: Databricks Free Edition, warehouse Serverless Starter Warehouse 2X-Small
- **Comparacion**: row count + primera celda (loose match, float con atol=1e-3)
- **Tiempo total**: 14.8 min (full eval sin contar GT cache)
- **GT cache**: pre-computado en `data/eval/eval_gt.json` (regenerable con `--force-gt`)

Fuente de verdad: `data/eval/eval_results.json` (ver tambien `data/eval/README.md`). El JSON nota un **merged run**: 12 preguntas re-corridas con el prompt nuevo; las otras 18 se arrastran de un run previo que ya estaba OK.

## Metricas agregadas (current)

| Metrica | Valor |
|---|---|
| Questions evaluated | 30 |
| **Execution success** | **100% (30/30)** (queries ejecutaron sin error) |
| **Execution accuracy** | **100% (30/30)** (resultados matchearon GT) |
| Exact SQL match | 0% (cosmetic — aliases/spacing difieren) |
| Latency p50 | 25.7s |
| Latency p95 | 76.0s |
| Latency max | 78.7s |
| Retries avg | 0.00 |

## Por categoria

| Categoria | n | ok% | acc% | avg_ms |
|---|---|---|---|---|
| single_table_aggregate | 4 | 100% | 100% | 25.4s |
| single_table_filter | 2 | 100% | 100% | 51.5s |
| two_table_join | 5 | 100% | 100% | 39.9s |
| three_table_join | 5 | 100% | 100% | 26.1s |
| group_by_order | 6 | 100% | 100% | 25.4s |
| having_subquery | 3 | 100% | 100% | 34.5s |
| edge_case | 5 | 100% | 100% | 28.7s |

Categorias 100% (current): aggregates, filtros WHERE, JOINs (2 y 3 tablas), group_by_order, HAVING, edge_case.

## Por dificultad

| Dificultad | n | acc% |
|---|---|---|
| easy | 8 | 100% |
| medium | 16 | 100% |
| hard | 6 | 100% |

## Historical snapshot (prior 93.3% / Q16 / Q28)

El snapshot **historico** anterior al prompt fix era **93.3%** (28/30). Las fallas **historicas** Q16 y Q28 estan abajo como prior snapshot; **no** son el resultado current. Current: **100% (30/30)** en `eval_results.json`.

### Q16 (historical) — Top 5 nations by total order revenue in 1995

- **Categoria**: group_by_order, medium
- **Pregunta**: "Top 5 nations by total order revenue in 1995."
- **Ground truth** (corregido a formula TPC-H estandar):
  ```sql
  SELECT n.n_name, sum(l.l_extendedprice * (1 - l.l_discount)) AS revenue
  FROM samples.tpch.lineitem l
  JOIN samples.tpch.orders o ON l.l_orderkey = o.o_orderkey
  JOIN samples.tpch.customer c ON o.o_custkey = c.c_custkey
  JOIN samples.tpch.nation n ON c.c_nationkey = n.n_nationkey
  WHERE year(o_orderdate) = 1995
  GROUP BY n.n_name ORDER BY revenue DESC LIMIT 5
  ```
- **SQL del agente**:
  ```sql
  SELECT n.n_name AS nation,
         SUM(l.l_extendedprice * (1 - l.l_discount)) AS total_revenue
  FROM samples.tpch.nation n
  JOIN samples.tpch.supplier s ON ...
  -- (sin WHERE year(o_orderdate) = 1995)
  ```
- **Causa**: el agente JOINa por lineitem pero pierde el filtro de ano sobre `o_orderdate`. Devuelve top 5 all-time en vez de 1995-only.
- **Fix sugerido** (Fase 9): prompt engineering — aclarar que cuando se filtra por ano de orden, el filtro va en `o_orderdate` (no en `l_shipdate`).

### Q28 (historical) — How many orders contain at least 5 line items

- **Categoria**: edge_case, hard
- **Pregunta**: "How many orders contain at least 5 line items?"
- **Ground truth**:
  ```sql
  SELECT count(*) FROM (
    SELECT l_orderkey, count(*) AS cnt
    FROM samples.tpch.lineitem
    GROUP BY l_orderkey
    HAVING count(*) >= 5
  )
  ```
- **SQL del agente** (malformado):
  ```sql
  SELECT count(DISTINCT l_orderkey) AS order_count
  FROM samples.tpch.lineitem
  GROUP BY l_orderkey
  HAVING count(l_linenumber) >= 5
  LIMIT 1000
  ```
- **Causa**: el `GROUP BY l_orderkey` sin una agregacion outer hace que el query devuelva counts per-orderkey, no un solo numero. Estructuralmente incorrecto.
- **Fix sugerido** (Fase 9): prompt engineering — aclarar que cuando se pide "count of X que cumplen Y", el patron canonico es `SELECT count(*) FROM (subquery con GROUP BY + HAVING)`.

## Lecciones aprendidas

1. **TPC-H revenue formula** es `extendedprice * (1 - discount)`, NO `extendedprice` solo. El LLM lo sabe; el GT mio original estaba mal. Lección: cuando el LLM y el GT discrepan en revenue, chequear el GT primero.
2. **Schema awareness**: el LLM "ve" las tablas y JOIN paths, pero a veces pierde filtros de ano cuando cambia el orden de los JOINs. Anotar explicitamente "filtros temporales van en la tabla de la fecha, no en tablas intermedias" en el prompt del SQL generator.
3. **Subquery patterns**: el LLM entiende HAVING pero no siempre el wrapping pattern `count(*) FROM (subquery)`. Vale la pena un ejemplo canonico en el prompt.
4. **Loose match funciona bien** para portfolio: 30 preguntas × ~25s = 12-15 min, que es razonable. Para benchmarks academicos usaria una comparacion de result sets completa (set equality), pero para portfolio es overkill.
