# -*- coding: utf-8 -*-
"""Migración: agrega fecha_salida y doc_salida a la tabla llantas.

Especificación: ESPECIFICACIONES_DELCA_v2.1.docx (sección 5.1) — la llanta
registra la fecha de salida y el documento de salida (salidas por fecha).

- Crea un backup de la BD antes de modificar.
- Agrega las columnas solo si no existen (idempotente).
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

COLUMNAS = [
    ("fecha_salida", "DATETIME"),
    ("doc_salida", "VARCHAR(100)"),
]


def main() -> None:
    if not os.path.exists(DB):
        print(f"ERROR: no existe la BD: {DB}")
        sys.exit(1)

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_backup_{ts}.db")
    shutil.copy2(DB, backup)
    print(f"Backup creado: {backup}")

    con = sqlite3.connect(DB)
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(llantas)").fetchall()]
        for nombre, tipo in COLUMNAS:
            if nombre in cols:
                print(f"La columna '{nombre}' ya existe — sin cambios.")
            else:
                con.execute(f"ALTER TABLE llantas ADD COLUMN {nombre} {tipo}")
                print(f"Columna '{nombre}' agregada a llantas.")
        con.commit()

        cols = [r[1] for r in con.execute("PRAGMA table_info(llantas)").fetchall()]
        print("Columnas llantas:", cols)
        print("MIGRACIÓN OK")
    finally:
        con.close()


if __name__ == "__main__":
    main()