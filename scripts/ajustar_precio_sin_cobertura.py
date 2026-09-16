# -*- coding: utf-8 -*-
"""Pone precio_venta = 1 (un peso) a las llantas SIN cobertura en el catálogo de precios.

Cobertura = existe precios_producto con (dimension_id, diseno_id) de la llanta.
El reporte de llantas ya resuelve el precio desde el catálogo (con fallback a 1 peso);
este script sincroniza el DATO de la llanta para el resto de la herramienta.

Uso: python scripts/ajustar_precio_sin_cobertura.py [--dry-run | --ejecutar]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "delca.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def main() -> None:
    parser = argparse.ArgumentParser(description="Precio 1 peso para llantas sin cobertura en el catálogo")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo simula (por defecto)")
    grupo.add_argument("--ejecutar", action="store_true", help="Aplica con backup")
    args = parser.parse_args()
    ejecutar = args.ejecutar

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Llantas sin cobertura (dim+dis no existe en precios_producto)
    sin_cob = con.execute("""
        SELECT l.id, l.tiquete, l.dimension_id, l.diseno_id, l.precio_venta
        FROM llantas l
        WHERE (l.dimension_id IS NULL OR l.diseno_id IS NULL)
           OR NOT EXISTS (
               SELECT 1 FROM precios_producto p
               WHERE p.dimension_id = l.dimension_id AND p.diseno_id = l.diseno_id
           )
    """).fetchall()

    print(f"[SIN COBERTURA] llantas: {len(sin_cob)}")
    for r in sin_cob[:10]:
        print(f"    {r['tiquete']} (dim={r['dimension_id']}, dis={r['diseno_id']}) precio_actual={r['precio_venta']}")

    # De las que tienen precio_venta != 1 (o NULL), cuántas se ajustarán
    a_ajustar = [r for r in sin_cob if (r["precio_venta"] or 0) != 1]
    print(f"[A AJUSTAR a 1 peso]: {len(a_ajustar)}")

    if not ejecutar:
        print("\n[DRY-RUN] No se escribio nada. Usa --ejecutar para aplicar.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_precio_sin_cob_{ts}.db")
    shutil.copy2(DB_PATH, backup)
    print(f"[BACKUP] {backup}")

    con.execute("BEGIN")
    for r in a_ajustar:
        con.execute("UPDATE llantas SET precio_venta = 1 WHERE id = ?", (r["id"],))
    con.commit()
    print(f"[OK] Ajustadas {len(a_ajustar)} llantas a precio 1 peso.")


if __name__ == "__main__":
    main()