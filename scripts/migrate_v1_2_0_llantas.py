"""Migration v1.2.0: Add catalog tables + new technical fields for Llantas.

Creates marcas_llanta, medidas_llanta, disenos_llanta tables
and adds new columns to the llantas table.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "delca.db")

_MIGRATION_TAG = "_migrated_v1_2_0"


def _is_applied(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        ("marcas_llanta",),
    ).fetchone()
    return row is not None


def run_migration() -> bool:
    if not os.path.exists(DB_PATH):
        print("[migracion] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")

    try:
        if _is_applied(conn):
            print("[OK] Migracion v1.2.0 ya aplicada — saltando.")
            return True

        # ── Create catalog tables ─────────────────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS marcas_llanta (
                id INTEGER NOT NULL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL UNIQUE
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medidas_llanta (
                id INTEGER NOT NULL PRIMARY KEY,
                ancho INTEGER NOT NULL,
                perfil INTEGER NOT NULL,
                rin INTEGER NOT NULL,
                UNIQUE (ancho, perfil, rin)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS disenos_llanta (
                id INTEGER NOT NULL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                marca_id INTEGER NOT NULL REFERENCES marcas_llanta(id) ON DELETE CASCADE,
                UNIQUE (nombre, marca_id)
            );
        """)

        # ── Add new columns to llantas table ──────────────────────────
        new_columns = [
            "marca_id INTEGER",
            "medida_id INTEGER",
            "diseno_id INTEGER",
            "ancho INTEGER",
            "perfil INTEGER",
            "rin INTEGER",
            "indice_carga VARCHAR(10)",
            "velocidad VARCHAR(5)",
            "capas VARCHAR(50)",
            "peso_maximo FLOAT",
            "posicion VARCHAR(50)",
            "rendimiento_km INTEGER",
            "costo_produccion FLOAT",
            "precio_venta FLOAT",
        ]

        for col_def in new_columns:
            col_name = col_def.split()[0]
            # Check if column already exists
            cursor = conn.execute("PRAGMA table_info(llantas)")
            existing = {row[1] for row in cursor.fetchall()}
            if col_name not in existing:
                conn.execute(f"ALTER TABLE llantas ADD COLUMN {col_def};")
                print(f"  -> Columna '{col_name}' agregada a llantas.")

        conn.commit()
        print("[OK] Migracion v1.2.0: tablas de catálogo + campos técnicos agregados.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migracion v1.2.0 fallo: {e}")
        return False

    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()


if __name__ == "__main__":
    run_migration()
