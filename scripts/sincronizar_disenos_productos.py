# -*- coding: utf-8 -*-
"""Sincroniza los diseños de banda con los productos de Materia Prima (Kardex).

Cada diseño de banda sin producto de MP correspondiente recibe un producto
'Banda {diseño}' (SKU 'BANDA{...}', unidad ROLLO, todo en 0) para que esté
disponible en el Kardex (Ingreso/Salida/Ajuste).

Uso: python scripts/sincronizar_disenos_productos.py [--dry-run | --ejecutar]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import unicodedata
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "delca.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def sku_diseno(nombre_diseno: str) -> str:
    s = unicodedata.normalize("NFD", nombre_diseno)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return "BANDA" + re.sub(r"[^0-9A-Za-z]", "", s.upper())[:50]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincronizar diseños de banda con productos MP")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo simula (por defecto)")
    grupo.add_argument("--ejecutar", action="store_true", help="Aplica con backup")
    args = parser.parse_args()
    ejecutar = args.ejecutar

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    disenos = con.execute("SELECT id, nombre FROM disenos_llanta ORDER BY nombre").fetchall()
    crear = []
    for d in disenos:
        nombre_banda = "Banda {}".format(d["nombre"])
        sku = sku_diseno(d["nombre"])
        # El diseño YA tiene producto si algún producto MP contiene su nombre
        # (ej. diseño 'DVRT4' -> producto 'Banda DVRT4 242').
        existe = con.execute(
            "SELECT 1 FROM productos WHERE nombre LIKE ? OR sku = ?",
            ("%{}%".format(d["nombre"]), sku),
        ).fetchone()
        if not existe:
            crear.append({"diseno_id": d["id"], "nombre": d["nombre"], "nombre_banda": nombre_banda, "sku": sku})

    print("Diseños totales:", len(disenos))
    print("A crear (diseños sin producto MP):", len(crear))
    for c in crear:
        print("  {} -> {} (sku={})".format(c["nombre"], c["nombre_banda"], c["sku"]))

    if not ejecutar:
        print("\n[DRY-RUN] No se escribio nada. Usa --ejecutar para aplicar.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_sync_disenos_{ts}.db")
    shutil.copy2(DB_PATH, backup)
    print(f"\n[BACKUP] {backup}")

    con.execute("BEGIN")
    for c in crear:
        con.execute(
            "INSERT INTO productos (nombre, sku, descripcion, categoria, stock, stock_kg, "
            "stock_minimo, costo_unitario, precio_venta, unidad_medida, activo) "
            "VALUES (?, ?, NULL, 'MATERIA_PRIMA', 0, 0, 0, 0, 0, 'ROLLO', 1)",
            (c["nombre_banda"], c["sku"]),
        )
    con.commit()
    print(f"[OK] Creados {len(crear)} productos de MP para los diseños de banda.")


if __name__ == "__main__":
    main()