"""
Migration v1.5.0: Eliminate PRODUCCION_DETENIDA from reglas_automatizacion.

Recreates the table to:
1. Remove PRODUCCION_DETENIDA from the CHECK constraint
2. Add the CHECK constraints that were defined in the model but missing from SQLite
3. Add the ix_reglas_tipo index that was defined but missing
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "delca.db")


def _has_old_tipo_constraint(conn: sqlite3.Connection) -> bool:
    """Check if the table still allows PRODUCCION_DETENIDA."""
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='reglas_automatizacion'"
    ).fetchone()
    if not sql:
        return False  # table doesn't exist
    return "PRODUCCION_DETENIDA" in (sql[0] or "")


def _has_correct_schema(conn: sqlite3.Connection) -> bool:
    """Check if the table already has the correct constraints (no PRODUCCION_DETENIDA)."""
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='reglas_automatizacion'"
    ).fetchone()
    if not sql:
        return True  # table doesn't exist yet, will be created correctly
    ddl = sql[0] or ""
    # Correct if it has the new CHECK without PRODUCCION_DETENIDA
    return (
        "CHECK (tipo IN ('STOCK_BAJO','CARTERA_VENCIDA','LLANTAS_LISTAS'))" in ddl
    )


def _has_index(conn: sqlite3.Connection) -> bool:
    idx = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='ix_reglas_tipo'"
    ).fetchone()
    return idx is not None


def run_migration() -> bool:
    if not os.path.exists(DB_PATH):
        print("[migracion v1.5.0] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.execute("PRAGMA journal_mode=WAL;")

    try:
        # Check if already applied
        if _has_correct_schema(conn) and _has_index(conn):
            print("[OK] Migracion v1.5.0 ya aplicada — saltando.")
            return True

        # Check how many rows would be deleted
        old_count = conn.execute(
            "SELECT COUNT(*) FROM reglas_automatizacion"
        ).fetchone()[0]

        deleted = conn.execute(
            "SELECT COUNT(*) FROM reglas_automatizacion WHERE tipo='PRODUCCION_DETENIDA'"
        ).fetchone()[0]

        # Recreate table with correct schema
        conn.executescript("""
            BEGIN TRANSACTION;

            CREATE TABLE reglas_automatizacion_nuevo (
                id INTEGER NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                tipo VARCHAR(50) NOT NULL,
                nivel VARCHAR(20) NOT NULL,
                activa BOOLEAN NOT NULL DEFAULT 1,
                config_json TEXT,
                created_at DATETIME NOT NULL,
                PRIMARY KEY (id),
                CHECK (tipo IN ('STOCK_BAJO','CARTERA_VENCIDA','LLANTAS_LISTAS')),
                CHECK (nivel IN ('INFO','WARNING','CRITICAL'))
            );

            INSERT INTO reglas_automatizacion_nuevo
                SELECT * FROM reglas_automatizacion
                WHERE tipo != 'PRODUCCION_DETENIDA';

            DROP TABLE reglas_automatizacion;

            ALTER TABLE reglas_automatizacion_nuevo RENAME TO reglas_automatizacion;

            CREATE INDEX ix_reglas_tipo ON reglas_automatizacion (tipo);

            COMMIT;
        """)

        new_count = conn.execute(
            "SELECT COUNT(*) FROM reglas_automatizacion"
        ).fetchone()[0]

        print(f"[OK] Migracion v1.5.0 completada.")
        print(f"    Filas antes: {old_count}")
        print(f"    Filas eliminadas (PRODUCCION_DETENIDA): {deleted}")
        print(f"    Filas despues: {new_count}")
        print(f"    CHECK constraint actualizado.")
        print(f"    Indice ix_reglas_tipo creado.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migracion v1.5.0 fallo: {e}")
        return False

    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()


if __name__ == "__main__":
    run_migration()
