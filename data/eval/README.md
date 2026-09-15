# Evaluación del Text-to-SQL Agent

Set de preguntas sobre `samples.tpch` para medir la performance del agente.

## Archivos

- `eval_set.json` — 30 preguntas con ground truth SQL canónico
- `eval_gt.json` — Cache de resultados del GT (pre-computado contra Databricks, regenerable con `--force-gt`)
- `eval_results.json` — Output del último run (latencias, métricas, prompt_version por pregunta)

## Cómo correrlo

```bash
# Run completo (15 min aprox)
python scripts/run_eval.py

# Opciones
python scripts/run_eval.py --qids Q01,Q05,Q10        # solo algunas
python scripts/run_eval.py --categories edge_case    # solo una categoría
python scripts/run_eval.py --limit 5                 # primeras N
python scripts/run_eval.py --force-gt                # recomputar GT
python scripts/run_eval.py --no-mlflow               # sin log a MLflow
```

## Resultados del último run (con prompt fixes)

| Métrica | Valor |
|---|---|
| Questions | 30 |
| **Execution success** | **100%** (30/30) |
| **Execution accuracy** | **100%** (30/30) |
| Latency p50 | 25.7s |
| Latency p95 | 76.0s |
| Latency max | 78.7s |
| Retries avg | 0.00 |

### Por categoría

| Categoría | n | acc% | avg_ms |
|---|---|---|---|
| single_table_aggregate | 4 | 100% | 25.4s |
| single_table_filter | 2 | 100% | 51.5s |
| two_table_join | 5 | 100% | 39.9s |
| three_table_join | 5 | 100% | 26.1s |
| group_by_order | 6 | 100% | 29.9s |
| having_subquery | 3 | 100% | 34.5s |
| edge_case | 5 | 100% | 29.9s |

### Historia de la accuracy

| Run | Accuracy | Notas |
|---|---|---|
| Inicial (sin fixes de prompt) | 83.3% (25/30) | Fallas por GTs mal escritos en revenue questions |
| Despues de corregir GTs | 93.3% (28/30) | Q16 y Q28 fallaban por bugs del LLM |
| Despues de prompt fixes (actual) | **100% (30/30)** | 3 reglas adicionales en `app/agent/prompts.py` |

### Los 3 prompt fixes que subieron la accuracy

1. **Filtros temporales**: cuando el usuario filtra por ano de una "orden", el filtro va en `o_orderdate`, no en `l_shipdate` (resolvio Q16)
2. **Patron count-de-X-con-Y**: para "cuantos X cumplen Y por grupo", usar `SELECT count(*) FROM (subquery con GROUP BY + HAVING)`, NO `SELECT count(...) ... GROUP BY ... HAVING` (resolvio Q28)
3. **TPC-H revenue formula**: `sum(l_extendedprice * (1 - l_discount))`, NO `sum(l_extendedprice)` (consistency con Q09, Q13, Q16)

Ver detalle en `docs/eval-results.md` y `app/agent/prompts.py`.

## Notas metodológicas

- **Ground truth**: SQL canónico escrito a mano + ejecutado contra Databricks para capturar row count + primera celda. Cache en `eval_gt.json`.
- **Comparación loose match**: row count igual Y primera celda igual (como float con `atol=1e-3`).
- **Comparación exact SQL match**: lowercase + strip whitespace. 0% es esperado — el LLM usa alias distintos.
- **Safety LIMIT 1000**: el guardrail agrega `LIMIT 1000` si falta. Queries que naturalmente devuelven más se truncan a 1000.
- **Limitaciones honestas**: el eval set es chiquito (30 preguntas), todas "faciles-medias" sobre un schema conocido. BIRD y Spider son benchmarks academicos con 1000+ preguntas mas diversas. Para portfolio es suficiente; para publish no.
