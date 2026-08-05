"""Migration v1.8.0: Add asesor column to llantas table."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "delca.db")


def run_migration() -> bool:
    if not os.path.exists(DB_PATH):
        print("[migracion] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.execute("PRAGMA table_info(llantas)")
        existing = {row[1] for row in cursor.fetchall()}

        if "asesor" not in existing:
            conn.execute("ALTER TABLE llantas ADD COLUMN asesor VARCHAR(200);")
            conn.commit()
            print("[OK] Columna 'asesor' agregada a llantas.")
        else:
            print("[OK] Columna 'asesor' ya existe — saltando.")

        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migracion v1.8.0 fallo: {e}")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
