"""Contract checks for notebooks/01_demo.ipynb schema cells (core arity + Spark keys)."""
import json
from pathlib import Path

NOTEBOOK = Path(__file__).resolve().parents[1] / "notebooks" / "01_demo.ipynb"


def _notebook_source() -> str:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    return "\n".join("".join(cell.get("source", [])) for cell in nb["cells"])


def test_list_tables_uses_catalog_and_schema_two_args():
    src = _notebook_source()
    assert "list_tables(settings.databricks_catalog, settings.databricks_schema)" in src
    assert "list_tables(settings.fqdn_target_table)" not in src


def test_describe_table_three_args_prints_spark_keys():
    src = _notebook_source()
    assert 'describe_table("samples", "tpch", table)' in src
    assert "col['col_name']" in src
    assert "col['data_type']" in src
    assert "col['name']" not in src
    assert "col['type']" not in src
    assert "for table in tables:" in src
