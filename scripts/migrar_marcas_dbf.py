"""Migración de marcas de llantas desde MAE_MARCA.DBF a la base DELCA v2.

Lee MAE_MARCA.DBF (dBASE/FoxPro) e inserta las marcas que no existan ya
(por nombre, case-insensitive). Mapea: MARCA -> nombre, COD_MARCA -> siglas.
Usa sqlite3 directo (patrón de las migraciones del proyecto).

Uso: python scripts/migrar_marcas_dbf.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sqlite3

import dbfread


DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "delca.db"
)
DBF_PATH = r"C:\Users\andre\OneDrive\Escritorio\DELCA\MAE_MARCA.DBF"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="No inserta, solo cuenta")
    args = parser.parse_args()

    db = dbfread.DBF(DBF_PATH, encoding="cp1252")
    filas = list(db)
    print(f"Registros leídos del DBF: {len(filas)}")

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    existentes = {
        str(r[0]).strip().upper()
        for r in cur.execute("SELECT nombre FROM marcas_llanta")
    }
    print(f"Marcas ya existentes en la DB: {len(existentes)}")

    insertados = 0
    omitidos = 0
    errores = 0
    ejemplos_error: list[str] = []

    for i, rec in enumerate(filas, start=1):
        nombre = str(rec["MARCA"]).strip()
        siglas = str(rec["COD_MARCA"]).strip()

        if not nombre:
            omitidos += 1
            continue
        if nombre.upper() in existentes:
            omitidos += 1
            continue

        try:
            if not args.dry_run:
                cur.execute(
                    "INSERT INTO marcas_llanta (nombre, siglas) VALUES (?, ?)",
                    (nombre, siglas or None),
                )
            insertados += 1
            if insertados <= 8:
                print(f"  [+] {nombre} | {siglas}")
        except Exception as e:  # noqa: BLE001
            errores += 1
            if len(ejemplos_error) < 5:
                ejemplos_error.append(f"fila {i} {nombre}: {e}")

    if not args.dry_run:
        con.commit()

    total = cur.execute("SELECT COUNT(*) FROM marcas_llanta").fetchone()[0]

    print("\n===== RESUMEN =====")
    print(f"Insertados: {insertados}")
    print(f"Omitidos (ya existían o vacíos): {omitidos}")
    print(f"Errores: {errores}")
    print(f"Total marcas en la DB ahora: {total}")
    for e in ejemplos_error:
        print("  ERROR:", e)

    con.close()


if __name__ == "__main__":
    main()
