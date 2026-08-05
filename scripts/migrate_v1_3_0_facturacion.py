"""Migration v1.3.0: Add plazo_dias column to facturas table.

Adds the plazo_dias (payment term in days) column required by the
Facturación view update for DELCA V2.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "delca.db")

_COLUMN = "plazo_dias"
_TAG = "_migrated_v1_3_0"


def _is_applied(conn: sqlite3.Connection) -> bool:
    cursor = conn.execute("PRAGMA table_info(facturas)")
    existing = {row[1] for row in cursor.fetchall()}
    return _COLUMN in existing


def run_migration() -> bool:
    if not os.path.exists(DB_PATH):
        print("[migracion] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")

    try:
        if _is_applied(conn):
            print("[OK] Migracion v1.3.0 ya aplicada — saltando.")
            return True

        conn.execute(
            f"ALTER TABLE facturas ADD COLUMN {_COLUMN} INTEGER DEFAULT 30;"
        )
        conn.commit()
        print("[OK] Migracion v1.3.0: columna 'plazo_dias' agregada a facturas.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migracion v1.3.0 fallo: {e}")
        return False

    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()


if __name__ == "__main__":
    run_migration()
