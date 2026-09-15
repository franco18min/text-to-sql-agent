"""
REFERENCIA HISTÓRICA — Chinook DB local (SQLite).

Este script fue el setup original del proyecto antes de migrar a Databricks.
El proyecto ahora usa `samples.tpch` directamente desde Unity Catalog (Databricks Free Edition).

Lo dejamos en el repo como referencia para:
- Demostrar la migración SQLite -> Databricks (talking point para entrevistas)
- Permitir correr una versión "lite" del agente sin Databricks (útil para debugging offline)
- Documentar el lineage del proyecto

Si querés usarlo:
    pip install sqlalchemy
    python scripts/setup_chinook_local.py

Para usar el agente con este setup local, hay que:
1. Tener `chinook.db` en data/db/
2. Sobreescribir temporalmente el connector (no incluido)
"""
import sqlite3
import urllib.request
from pathlib import Path
import sys

CHINOOK_URL = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite"
DB_PATH = Path("./data/db/chinook.db")


def download_chinook():
    """Descarga el archivo SQLite de Chinook (sample iTunes-style)."""
    if DB_PATH.exists():
        print(f"[OK] DB ya existe en {DB_PATH}")
        return

    print("[..] Descargando Chinook DB desde GitHub...")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        urllib.request.urlretrieve(CHINOOK_URL, DB_PATH)
        print(f"[OK] Descargado: {DB_PATH}")
    except Exception as e:
        print(f"[FAIL] Error descargando: {e}")
        sys.exit(1)


def verify_db():
    """Verifica que la DB esté bien cargada y muestra info."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"\n[INFO] Tablas en la DB ({len(tables)}):")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f"   - {table}: {count} filas")

    print("\n[INFO] Schema de tablas principales:")
    for table in ["Artist", "Album", "Track", "Customer", "Invoice"]:
        if table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            cols = cursor.fetchall()
            print(f"\n   {table}:")
            for col in cols:
                col_id, col_name, col_type, _, _, _ = col
                print(f"     {col_name} ({col_type})")

    print("\n[INFO] Top 5 artistas con más tracks:")
    cursor.execute("""
        SELECT ar.Name, COUNT(t.TrackId) as track_count
        FROM Artist ar
        JOIN Album al ON ar.ArtistId = al.ArtistId
        JOIN Track t ON al.AlbumId = t.AlbumId
        GROUP BY ar.ArtistId
        ORDER BY track_count DESC
        LIMIT 5;
    """)
    for row in cursor.fetchall():
        print(f"   - {row[0]}: {row[1]} tracks")

    conn.close()
    print(f"\n[OK] Chinook DB lista en {DB_PATH}")


if __name__ == "__main__":
    print("=" * 60)
    print("REFERENCIA HISTORICA - Chinook DB local (no usado por el agente)")
    print("El proyecto actual usa samples.tpch en Databricks.")
    print("=" * 60)
    download_chinook()
    verify_db()
