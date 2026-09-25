"""Migración de clientes desde CSV a la base DELCA v2.

Lee 'Clientes 1 18-08.csv' e inserta los clientes que no existan ya (por NIT).
Conserva nombre, nit, telefono, celular, email, direccion. Ciudad = None.
Usa sqlite3 directo (patrón de las migraciones del proyecto).

Uso: python scripts/migrar_clientes_csv.py [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import io
import sqlite3
import os


DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "delca.db"
)
CSV_PATH = os.environ.get("DELCA_ARCHIVO_CLIENTES_MIGRAR", r"C:\Users\andre\OneDrive\Escritorio\DELCA\Clientes 1 18-08.csv")


def leer_csv() -> list[dict]:
    with io.open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def norm(valor: str | None) -> str | None:
    if valor is None:
        return None
    v = valor.strip()
    return v if v else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="No inserta, solo cuenta")
    args = parser.parse_args()

    filas = leer_csv()
    print(f"Filas leídas del CSV: {len(filas)}")

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.cursor()

    nits_existentes = {str(r[0]).strip() for r in cur.execute("SELECT nit FROM cliente")}
    print(f"NIT ya existentes en la DB: {len(nits_existentes)}")

    insertados = 0
    omitidos = 0
    errores = 0
    ejemplos_error: list[str] = []

    for i, fila in enumerate(filas, start=2):
        nombre = norm(fila.get("nombre"))
        nit = norm(fila.get("nit"))
        if not nombre or not nit:
            omitidos += 1
            continue
        if nit in nits_existentes:
            omitidos += 1
            continue

        telefono = norm(fila.get("telefono"))
        celular = norm(fila.get("celular"))
        email = norm(fila.get("email"))
        direccion = norm(fila.get("direccion"))

        try:
            if not args.dry_run:
                cur.execute(
                    "INSERT INTO cliente "
                    "(nombre, nit, telefono, celular, email, direccion, ciudad, "
                    " saldo, activo, categoria_abc) "
                    "VALUES (?, ?, ?, ?, ?, ?, NULL, 0, 1, 'B')",
                    (nombre, nit, telefono, celular, email, direccion),
                )
            insertados += 1
            if insertados <= 5:
                print(f"  [+] {nombre} | {nit} | tel:{telefono} | cel:{celular}")
        except Exception as e:  # noqa: BLE001
            errores += 1
            if len(ejemplos_error) < 5:
                ejemplos_error.append(f"fila {i} {nombre}: {e}")

    if not args.dry_run:
        con.commit()

    # Total final en la DB
    total = cur.execute("SELECT COUNT(*) FROM cliente").fetchone()[0]

    print("\n===== RESUMEN =====")
    print(f"Insertados: {insertados}")
    print(f"Omitidos (ya existían o sin nombre/nit): {omitidos}")
    print(f"Errores: {errores}")
    print(f"Total clientes en la DB ahora: {total}")
    for e in ejemplos_error:
        print("  ERROR:", e)

    con.close()


if __name__ == "__main__":
    main()
