"""Migration v1.4.0: Rename precio_compra to costo_produccion in llantas.

Aligns the column name with the business reality: this value represents
the tire's manufacturing/production cost, not a purchase price.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "delca.db")


def _has_old_column(conn: sqlite3.Connection) -> bool:
    cursor = conn.execute("PRAGMA table_info(llantas)")
    return any(row[1] == "precio_compra" for row in cursor.fetchall())


def _has_new_column(conn: sqlite3.Connection) -> bool:
    cursor = conn.execute("PRAGMA table_info(llantas)")
    return any(row[1] == "costo_produccion" for row in cursor.fetchall())


def run_migration() -> bool:
    if not os.path.exists(DB_PATH):
        print("[migracion] delca.db no encontrado - saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")

    try:
        if _has_new_column(conn) and not _has_old_column(conn):
            print("[OK] Migracion v1.4.0 ya aplicada - saltando.")
            return True

        if not _has_old_column(conn):
            print("[OK] Columna 'precio_compra' no existe - saltando.")
            return True

        conn.execute(
            "ALTER TABLE llantas RENAME COLUMN precio_compra TO costo_produccion;"
        )
        conn.commit()
        print("[OK] Migracion v1.4.0: columna renombrada 'precio_compra' -> 'costo_produccion'.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migracion v1.4.0 fallo: {e}")
        # Fallback: SQLite < 3.25 doesn't support RENAME COLUMN
        print("[migracion] Su SQLite podria ser anterior a 3.25.")
        print("[migracion] Ejecute manualmente o actualice SQLite.")
        return False

    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()


if __name__ == "__main__":
    run_migration()
