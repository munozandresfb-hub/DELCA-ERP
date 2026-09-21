# -*- coding: utf-8 -*-
"""Migración: agrega la columna causa_rechazo_id a la tabla llantas.

Especificación: ESPECIFICACIONES_DELCA_v2.1.docx (sección 5.1) — la llanta
guarda la causa de rechazo de inspección (obligatoria cuando estado = RECHAZADA).

- Crea un backup de la BD antes de modificar.
- Agrega la columna solo si no existe (idempotente).
- Verifica que la tabla causas_rechazo esté poblada.
"""
import os
import shutil
import sqlite3
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "delca.db")
BACKUP_DIR = os.path.join(BASE, "backups", "migracion")

COLUMNA = "causa_rechazo_id"


def main() -> None:
    if not os.path.exists(DB):
        print(f"ERROR: no existe la BD: {DB}")
        sys.exit(1)

    # 1) Backup
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_backup_{ts}.db")
    shutil.copy2(DB, backup)
    print(f"Backup creado: {backup}")

    con = sqlite3.connect(DB)
    try:
        # 2) Verificar causas_rechazo
        n_causas = con.execute(
            "SELECT COUNT(*) FROM causas_rechazo"
        ).fetchone()[0]
        print(f"causas_rechazo: {n_causas} registros")
        if n_causas == 0:
            print("ADVERTENCIA: la tabla causas_rechazo está vacía.")

        # 3) Agregar columna si no existe
        cols = [r[1] for r in con.execute("PRAGMA table_info(llantas)").fetchall()]
        if COLUMNA in cols:
            print(f"La columna '{COLUMNA}' ya existe — no se modifica nada.")
        else:
            con.execute(
                f"ALTER TABLE llantas ADD COLUMN {COLUMNA} INTEGER "
                "REFERENCES causas_rechazo(id)"
            )
            print(f"Columna '{COLUMNA}' agregada a llantas.")
        con.commit()

        # 4) Verificar estado final
        cols = [r[1] for r in con.execute("PRAGMA table_info(llantas)").fetchall()]
        print("Columnas llantas:", cols)
        print("MIGRACIÓN OK")
    finally:
        con.close()


if __name__ == "__main__":
    main()