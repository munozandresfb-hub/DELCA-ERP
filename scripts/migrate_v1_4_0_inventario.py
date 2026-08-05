"""Migration v1.4.0: Create inventory configuration tables.

Adds three tables:
- costos_produccion_estandar: standard mfg cost per design + dimension
- precios_venta_cliente: sale price per client + design + dimension
- recetas_produccion: raw material consumption per design + dimension
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "delca.db")

TABLES = {
    "costos_produccion_estandar": """
        CREATE TABLE IF NOT EXISTS costos_produccion_estandar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diseno_id INTEGER NOT NULL REFERENCES disenos_llanta(id) ON DELETE CASCADE,
            medida_id INTEGER NOT NULL REFERENCES medidas_llanta(id) ON DELETE CASCADE,
            costo_produccion NUMERIC(12,2) NOT NULL DEFAULT 0,
            UNIQUE(diseno_id, medida_id)
        )
    """,
    "precios_venta_cliente": """
        CREATE TABLE IF NOT EXISTS precios_venta_cliente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL REFERENCES cliente(id) ON DELETE CASCADE,
            diseno_id INTEGER NOT NULL REFERENCES disenos_llanta(id) ON DELETE CASCADE,
            medida_id INTEGER NOT NULL REFERENCES medidas_llanta(id) ON DELETE CASCADE,
            precio_venta NUMERIC(12,2) NOT NULL DEFAULT 0,
            UNIQUE(cliente_id, diseno_id, medida_id)
        )
    """,
    "recetas_produccion": """
        CREATE TABLE IF NOT EXISTS recetas_produccion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            diseno_id INTEGER NOT NULL REFERENCES disenos_llanta(id) ON DELETE CASCADE,
            medida_id INTEGER NOT NULL REFERENCES medidas_llanta(id) ON DELETE CASCADE,
            producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
            cantidad NUMERIC(12,2) NOT NULL DEFAULT 0,
            unidad VARCHAR(20) NOT NULL DEFAULT 'UNIDAD',
            UNIQUE(diseno_id, medida_id, producto_id)
        )
    """,
}


def run_migration() -> bool:
    if not os.path.exists(DB_PATH):
        print("[migracion] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")

    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing = {row[0] for row in cursor.fetchall()}

        created = 0
        for name, ddl in TABLES.items():
            if name not in existing:
                conn.execute(ddl)
                created += 1
                print(f"[OK] Tabla '{name}' creada.")

        conn.commit()
        if created == 0:
            print("[OK] Migracion v1.4.0 ya aplicada — saltando.")
        else:
            print(f"[OK] Migracion v1.4.0: {created} tabla(s) creada(s).")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migracion v1.4.0 fallo: {e}")
        return False

    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()


if __name__ == "__main__":
    run_migration()
