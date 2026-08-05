"""
Migration utility — ensures each migration runs exactly once.
Uses a _migrations table in SQLite for idempotency tracking.
"""

from sqlalchemy import text


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
