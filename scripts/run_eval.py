"""
Eval runner — Fase 8.

Para cada pregunta en `data/eval/eval_set.json`:
1. Corre el SQL canónico contra Databricks y captura el ground truth (GT).
2. Invoca el agente con la pregunta.
3. Compara el resultado del agente contra el GT.

Métricas:
- execution_success: % de Q donde la query ejecutó sin error
- execution_accuracy: % donde (row_count == GT.row_count) AND (first_cell == GT.first_cell)
  (loose match — counts/avg/sum pueden ser int o float, comparo como float)
- exact_sql_match: % donde el SQL generado (normalizado) matchea exactamente el GT
- latency_p50, p95, max
- retries_avg
- breakdown por categoría

Outputs:
- data/eval/eval_results.json (resultado completo, pregunta por pregunta)
- stdout: tabla resumen

Uso:
    python scripts/run_eval.py [--limit N] [--categories cat1,cat2] [--qids Q01,Q02]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Repo paths
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402  (after sys.path insert)
from app.core.db import execute_query  # noqa: E402
from app.agent.graph import run_agent  # noqa: E402


EVAL_DIR = ROOT / "data" / "eval"
EVAL_SET_PATH = EVAL_DIR / "eval_set.json"
RESULTS_PATH = EVAL_DIR / "eval_results.json"


# ============================================================
# SQL normalization for exact match
# ============================================================

def normalize_sql(sql: str | None) -> str:
    """
    Normaliza un SQL para comparar exact match:
    - Lowercase
    - Strip trailing ;
    - Collapse whitespace
    - Strip leading/trailing whitespace
    """
    if not sql:
        return ""
    s = sql.strip().rstrip(";").strip()
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def _to_float(v: Any) -> float | None:
    """Convierte una celda a float para comparación numérica. None si no se puede."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def result_matches_gt(actual: list[dict], gt: list[dict], atol: float = 1e-3) -> bool:
    """
    Loose match: mismo row count Y (si no están vacíos) la primera celda de la
    primera fila matchea como float dentro de `atol`.
    """
    if len(actual) != len(gt):
        return False
    if not gt and not actual:
        return True
    if not gt or not actual:
        return False
    a_first = list(actual[0].values())[0] if actual[0] else None
    g_first = list(gt[0].values())[0] if gt[0] else None
    a_f = _to_float(a_first)
    g_f = _to_float(g_first)
    if a_f is None and g_f is None:
        # comparación de strings
        return str(a_first).strip() == str(g_first).strip()
    if a_f is None or g_f is None:
        return False
    return abs(a_f - g_f) <= atol * max(1.0, abs(g_f))


# ============================================================
# GT cache
# ============================================================

def get_or_build_gt(questions: list[dict], force: bool = False) -> dict[str, list[dict]]:
    """
    Para cada Q, corre el ground_truth_sql contra Databricks y devuelve
    {qid: [row, ...]}. Cachea en data/eval/eval_gt.json.
    """
    cache_path = EVAL_DIR / "eval_gt.json"
    cache: dict[str, list[dict]] = {}
    if cache_path.exists() and not force:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    missing = [q for q in questions if q["id"] not in cache]
    if missing:
        print(f"\n[GT] Computando ground truth para {len(missing)} preguntas (Databricks)...")
        for q in missing:
            try:
                rows = execute_query(q["ground_truth_sql"], fetch=True) or []
                cache[q["id"]] = rows
                print(f"  {q['id']}: {len(rows)} filas  OK")
            except Exception as e:
                print(f"  {q['id']}: ERROR {e}")
                cache[q["id"]] = [{"_gt_error": f"{type(e).__name__}: {e}"}]
        cache_path.write_text(json.dumps(cache, indent=2, default=str), encoding="utf-8")
        print(f"[GT] Cache guardada en {cache_path}")
    else:
        print(f"[GT] Cache ya existe ({len(cache)} Qs)")

    return cache


# ============================================================
# Eval runner
# ============================================================

def run_one_question(q: dict, gt: list[dict]) -> dict:
    """Corre UNA pregunta a través del agente y devuelve el resultado."""
    qid = q["id"]
    session_id = f"eval-{qid}"
    t0 = time.perf_counter()
    err_str = None
    agent_sql = None
    actual_results: list[dict] = []
    retry_count = 0
    answer = ""

    try:
        result = run_agent(question=q["question"], session_id=session_id)
        agent_sql = result.get("sql_query")
        actual_results = result.get("results") or []
        retry_count = int(result.get("retry_count", 0))
        answer = result.get("answer", "")
        err = result.get("error")
        if err:
            err_str = str(err)[:300]
    except Exception as e:
        err_str = f"{type(e).__name__}: {e}"[:300]

    # Wall-clock del wrapper (el agente no computa su propia latencia en state)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # Comparaciones
    exact_match = normalize_sql(agent_sql) == normalize_sql(q["ground_truth_sql"])
    loose_match = (
        err_str is None
        and result_matches_gt(actual_results, gt)
    )

    return {
        "id": qid,
        "category": q["category"],
        "difficulty": q["difficulty"],
        "question": q["question"],
        "ground_truth_sql": q["ground_truth_sql"],
        "ground_truth_rows": len(gt) if isinstance(gt, list) else 0,
        "ground_truth_first_cell": (
            list(gt[0].values())[0] if gt and isinstance(gt, list) and gt and not gt[0].get("_gt_error") else None
        ),
        "agent_sql": agent_sql,
        "agent_sql_normalized": normalize_sql(agent_sql),
        "agent_row_count": len(actual_results),
        "agent_first_cell": (
            list(actual_results[0].values())[0] if actual_results else None
        ),
        "execution_success": err_str is None,
        "execution_accuracy": loose_match,
        "exact_sql_match": exact_match,
        "retry_count": retry_count,
        "latency_ms": latency_ms,
        "answer": answer[:200],
        "error": err_str,
    }


def summarize(results: list[dict]) -> dict:
    """Calcula métricas agregadas."""
    n = len(results)
    if n == 0:
        return {}

    exec_success = sum(1 for r in results if r["execution_success"])
    exec_accuracy = sum(1 for r in results if r["execution_accuracy"])
    exact_match = sum(1 for r in results if r["exact_sql_match"])

    latencies = [r["latency_ms"] for r in results if r["execution_success"]]
    retries = [r["retry_count"] for r in results if r["execution_success"]]

    # Breakdown por categoría
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)
    cat_breakdown = {}
    for cat, rs in by_cat.items():
        n_cat = len(rs)
        cat_breakdown[cat] = {
            "count": n_cat,
            "execution_success_pct": 100.0 * sum(1 for r in rs if r["execution_success"]) / n_cat,
            "execution_accuracy_pct": 100.0 * sum(1 for r in rs if r["execution_accuracy"]) / n_cat,
            "exact_sql_match_pct": 100.0 * sum(1 for r in rs if r["exact_sql_match"]) / n_cat,
            "avg_latency_ms": statistics.mean(r["latency_ms"] for r in rs) if rs else 0.0,
        }

    return {
        "n_questions": n,
        "execution_success_pct": 100.0 * exec_success / n,
        "execution_accuracy_pct": 100.0 * exec_accuracy / n,
        "exact_sql_match_pct": 100.0 * exact_match / n,
        "latency_p50_ms": statistics.median(latencies) if latencies else 0.0,
        "latency_p95_ms": (
            sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 5
            else (max(latencies) if latencies else 0.0)
        ),
        "latency_max_ms": max(latencies) if latencies else 0.0,
        "retries_avg": statistics.mean(retries) if retries else 0.0,
        "by_category": cat_breakdown,
    }


def print_summary_table(summary: dict, results: list[dict]) -> None:
    """Imprime tabla resumen en stdout."""
    print("\n" + "=" * 80)
    print("EVAL SUMMARY")
    print("=" * 80)
    print(f"  Questions evaluated:        {summary['n_questions']}")
    print(f"  Execution success:          {summary['execution_success_pct']:.1f}%")
    print(f"  Execution accuracy:         {summary['execution_accuracy_pct']:.1f}%")
    print(f"  Exact SQL match:            {summary['exact_sql_match_pct']:.1f}%")
    print(f"  Latency p50:                {summary['latency_p50_ms']:.0f} ms")
    print(f"  Latency p95:                {summary['latency_p95_ms']:.0f} ms")
    print(f"  Latency max:                {summary['latency_max_ms']:.0f} ms")
    print(f"  Retries avg:                {summary['retries_avg']:.2f}")

    print("\n  By category:")
    print(f"  {'category':<25} {'n':>4} {'ok%':>6} {'acc%':>6} {'sql%':>6} {'avg_ms':>8}")
    print("  " + "-" * 60)
    for cat, m in summary["by_category"].items():
        print(
            f"  {cat:<25} {m['count']:>4} "
            f"{m['execution_success_pct']:>5.1f}% "
            f"{m['execution_accuracy_pct']:>5.1f}% "
            f"{m['exact_sql_match_pct']:>5.1f}% "
            f"{m['avg_latency_ms']:>7.0f}"
        )

    # Failures detail
    failed = [r for r in results if not r["execution_accuracy"]]
    if failed:
        print(f"\n  Failures ({len(failed)}):")
        for r in failed:
            err = r["error"] or "result mismatch"
            err = err[:80].replace("\n", " ")
            print(f"    {r['id']} [{r['category']}]: {err}")
            if r["agent_sql"]:
                print(f"      agent:   {r['agent_sql'][:120]}")
            print(f"      expected:{r['ground_truth_sql'][:120]}")


# ============================================================
# MLflow logging (best-effort)
# ============================================================

def log_to_mlflow(summary: dict, results: list[dict]) -> None:
    """Loggea métricas agregadas a MLflow. No-op si no se puede configurar."""
    try:
        from app.observability import configure_mlflow, log_metric, log_param
        configure_mlflow()
        run_name = f"eval-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        import mlflow
        with mlflow.start_run(run_name=run_name):
            log_param("n_questions", summary["n_questions"])
            log_param("model", settings.gemini_model)
            log_param("memory_type", settings.memory_type)
            log_metric("execution_success_pct", summary["execution_success_pct"])
            log_metric("execution_accuracy_pct", summary["execution_accuracy_pct"])
            log_metric("exact_sql_match_pct", summary["exact_sql_match_pct"])
            log_metric("latency_p50_ms", summary["latency_p50_ms"])
            log_metric("latency_p95_ms", summary["latency_p95_ms"])
            log_metric("latency_max_ms", summary["latency_max_ms"])
            log_metric("retries_avg", summary["retries_avg"])
            for cat, m in summary["by_category"].items():
                log_metric(f"cat.{cat}.accuracy_pct", m["execution_accuracy_pct"])
        print("\n[MLflow] Métricas loggeadas (degraded silently si no hay auth)")
    except Exception as e:
        print(f"\n[MLflow] No se pudo loggear (no bloquea): {type(e).__name__}: {e}")


# ============================================================
# Main
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Run the eval set against the agent")
    parser.add_argument("--limit", type=int, default=None, help="Solo las primeras N preguntas")
    parser.add_argument("--categories", type=str, default=None, help="Filtrar por categorías (csv)")
    parser.add_argument("--qids", type=str, default=None, help="Filtrar por IDs (csv, ej. 'Q01,Q05')")
    parser.add_argument("--force-gt", action="store_true", help="Recalcular GT cache")
    parser.add_argument("--no-mlflow", action="store_true", help="Saltear logging a MLflow")
    args = parser.parse_args()

    if not EVAL_SET_PATH.exists():
        print(f"ERROR: no se encontró {EVAL_SET_PATH}")
        return 1

    eval_set = json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))
    questions = eval_set["questions"]
    print(f"[eval] Cargadas {len(questions)} preguntas del eval set v{eval_set.get('version')}")

    # Filtros
    if args.qids:
        keep = set(s.strip() for s in args.qids.split(","))
        questions = [q for q in questions if q["id"] in keep]
        print(f"[eval] Filtrado a {len(questions)} Q por --qids")
    if args.categories:
        keep = set(s.strip() for s in args.categories.split(","))
        questions = [q for q in questions if q["category"] in keep]
        print(f"[eval] Filtrado a {len(questions)} Q por --categories")
    if args.limit:
        questions = questions[:args.limit]
        print(f"[eval] Limitado a {len(questions)} Q por --limit")

    # GT (cache)
    gt_cache = get_or_build_gt(questions, force=args.force_gt)

    # Run
    print(f"\n[eval] Corriendo agente en {len(questions)} preguntas...")
    print(f"[eval] model={settings.gemini_model}  memory={settings.memory_type}")
    t_start = time.perf_counter()
    results: list[dict] = []
    for i, q in enumerate(questions, 1):
        qid = q["id"]
        gt = gt_cache.get(qid, [])
        # Si el GT tuvo error, lo marcamos
        if isinstance(gt, list) and gt and isinstance(gt[0], dict) and "_gt_error" in gt[0]:
            results.append({
                "id": qid,
                "category": q["category"],
                "difficulty": q["difficulty"],
                "question": q["question"],
                "ground_truth_sql": q["ground_truth_sql"],
                "ground_truth_error": gt[0]["_gt_error"],
                "execution_success": False,
                "execution_accuracy": False,
                "exact_sql_match": False,
                "retry_count": 0,
                "latency_ms": 0.0,
                "error": f"GT failed: {gt[0]['_gt_error']}",
            })
            print(f"  [{i}/{len(questions)}] {qid} SKIP (GT error)")
            continue

        print(f"  [{i}/{len(questions)}] {qid} ({q['category']})...", end=" ", flush=True)
        r = run_one_question(q, gt)
        results.append(r)
        status = "OK" if r["execution_accuracy"] else ("ERR" if not r["execution_success"] else "WRONG")
        print(f"{status}  {r['latency_ms']:.0f}ms  retries={r['retry_count']}")

    total_s = (time.perf_counter() - t_start) / 60.0
    print(f"\n[eval] Completado en {total_s:.1f} min")

    # Summary
    summary = summarize(results)
    print_summary_table(summary, results)

    # Save
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": settings.gemini_model,
        "memory_type": settings.memory_type,
        "summary": summary,
        "results": results,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\n[eval] Resultados guardados en {RESULTS_PATH}")

    # MLflow
    if not args.no_mlflow:
        log_to_mlflow(summary, results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
