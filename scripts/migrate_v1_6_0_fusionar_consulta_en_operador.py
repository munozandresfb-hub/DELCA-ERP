"""
Migration v1.6.0: Merge CONSULTA role into OPERADOR.

Since CONSULTA was read-only and OPERADOR already includes all CONSULTA
permissions plus creation/editing, we eliminate the CONSULTA role and
reassign any CONSULTA users to OPERADOR.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "delca.db")


def run_migration() -> bool:
    if not os.path.exists(DB_PATH):
        print("[migracion v1.6.0] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")

    try:
        # Check if CONSULTA role exists
        consulta = conn.execute(
            "SELECT id FROM roles WHERE nombre='CONSULTA'"
        ).fetchone()

        if not consulta:
            print("[OK] Migracion v1.6.0 ya aplicada — no hay rol CONSULTA.")
            return True

        consulta_id = consulta[0]

        # Find OPERADOR role
        operador = conn.execute(
            "SELECT id FROM roles WHERE nombre='OPERADOR'"
        ).fetchone()
        if not operador:
            print("[ERROR] Migracion v1.6.0: No se encontro rol OPERADOR.")
            return False

        operador_id = operador[0]

        # Count users to migrate
        users_to_migrate = conn.execute(
            "SELECT COUNT(*) FROM usuarios WHERE rol_id=?", (consulta_id,)
        ).fetchone()[0]

        # Reassign users from CONSULTA to OPERADOR
        conn.execute(
            "UPDATE usuarios SET rol_id=? WHERE rol_id=?",
            (operador_id, consulta_id),
        )

        # Delete CONSULTA role (cascade will clean up roles_permisos)
        conn.execute("DELETE FROM roles WHERE id=?", (consulta_id,))

        conn.commit()

        print(f"[OK] Migracion v1.6.0 completada.")
        print(f"    Usuarios migrados CONSULTA -> OPERADOR: {users_to_migrate}")
        print(f"    Rol CONSULTA eliminado.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migracion v1.6.0 fallo: {e}")
        return False

    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()


if __name__ == "__main__":
    run_migration()
