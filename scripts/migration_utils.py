"""
Migration utility — ensures each migration runs exactly once.
Uses a _migrations table in SQLite for idempotency tracking.
"""

import shutil
import sqlite3

from sqlalchemy import text


def backup_seguro(origen: str, destino: str) -> str:
    """Copia de respaldo WAL-safe de una BD SQLite.

    Con ``journal_mode=WAL`` el archivo principal puede no contener los
    últimos cambios (viven en el ``-wal``). Ejecuta un checkpoint con
    truncado antes de copiar para que el respaldo sea consistente aunque
    la aplicación esté corriendo. Mismo patrón que
    ``src/core/services/backup_service.py``.

    Args:
        origen:  Ruta de la BD (ej. ``delca.db``).
        destino: Ruta del archivo de respaldo.

    Returns:
        La ruta del respaldo creado.
    """
    conn = sqlite3.connect(origen, timeout=10)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    shutil.copy2(origen, destino)
    return destino


def run_migration_once(version: str, import_path: str, func_name: str = "run_migration") -> None:
    """Import and run a migration only if it has not been applied yet.

    Args:
        version:  Unique version string (e.g. ``"v1.0.0"``).
        import_path:  Dot-separated module path to the migration script.
        func_name:  Name of the migration function inside the module.
    """
    from src.database.engine import engine

    # ── Ensure tracking table exists ───────────────────────────────────
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS _migrations ("
            "  version TEXT PRIMARY KEY,"
            "  applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        ))
        conn.commit()

        # Check if already applied
        result = conn.execute(
            text("SELECT version FROM _migrations WHERE version = :v"),
            {"v": version},
        ).fetchone()

        if result:
            print(f"[migrations] {version} ya aplicada, saltando")
            return

    # ── Run migration ─────────────────────────────────────────────────
    import importlib

    print(f"[migrations] Aplicando {version} …")
    try:
        mod = importlib.import_module(import_path)
        func = getattr(mod, func_name)
        func()
    except Exception:
        print(f"[migrations] ERROR en {version}")
        raise

    # ── Record as applied ─────────────────────────────────────────────
    with engine.connect() as conn:
        conn.execute(
            text("INSERT OR IGNORE INTO _migrations (version) VALUES (:v)"),
            {"v": version},
        )
        conn.commit()
    print(f"[migrations] {version} aplicada correctamente")
