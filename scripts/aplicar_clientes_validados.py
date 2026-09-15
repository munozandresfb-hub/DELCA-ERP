# -*- coding: utf-8 -*-
"""Aplica las 18 asignaciones de cliente + NIT validadas manualmente por el negocio (2026-09-15).

Asignaciones (tiquete -> cliente_id):
  ROSELLANTAS LTDA (DIST)  id 491, NIT 901585099: 1355, 1356
  ROBERTO LOPEZ            id 675, NIT 07211231:  6142, 13422
  GIRALDO RIVERA           id 672, NIT 005824600: 7206, 7207, 7208
  PEREZ ABELINO            id 506, NIT 0025865400: 12021, 12022
  GERARDO BRAVO            id 431, NIT 0025845600: 13351, 19826, 19827, 23486, 23487
  TORO JOSE DOMINGO        id 532, NIT 07307224:  14132, 14540, 15113, 17917

Además actualiza el NIT de los clientes con los valores reales proporcionados.
Uso: python scripts/aplicar_clientes_validados.py [--dry-run | --ejecutar]
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

CLIENTES = {
    491: {"nombre": "ROSELLANTAS LTDA (DIST)", "nit": "901585099"},
    675: {"nombre": "ROBERTO LOPEZ", "nit": "07211231"},
    672: {"nombre": "GIRALDO RIVERA", "nit": "005824600"},
    506: {"nombre": "PEREZ ABELINO", "nit": "0025865400"},
    431: {"nombre": "GERARDO BRAVO", "nit": "0025845600"},
    532: {"nombre": "TORO JOSE DOMINGO", "nit": "07307224"},
}

ASIGNACIONES = {
    "1355": 491, "1356": 491,
    "6142": 675, "13422": 675,
    "7206": 672, "7207": 672, "7208": 672,
    "12021": 506, "12022": 506,
    "13351": 431, "19826": 431, "19827": 431, "23486": 431, "23487": 431,
    "14132": 532, "14540": 532, "15113": 532, "17917": 532,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplicar 18 asignaciones de cliente + NIT validadas")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo simula (por defecto)")
    grupo.add_argument("--ejecutar", action="store_true", help="Aplica con backup")
    args = parser.parse_args()
    ejecutar = args.ejecutar

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print(f"Asignaciones: {len(ASIGNACIONES)} llantas | clientes con NIT: {len(CLIENTES)}")

    cambios = []
    for tq, cid in sorted(ASIGNACIONES.items()):
        r = con.execute("SELECT id, tiquete, cliente_id FROM llantas WHERE tiquete = ?", (tq,)).fetchone()
        if not r:
            print(f"  !! {tq} NO ENCONTRADA")
            continue
        actual = con.execute("SELECT nombre FROM cliente WHERE id = ?", (r["cliente_id"],)).fetchone() if r["cliente_id"] else None
        destino = CLIENTES[cid]["nombre"]
        cambios.append({
            "llanta_id": r["id"], "tiquete": tq,
            "actual_id": r["cliente_id"], "actual": actual["nombre"] if actual else "SIN CLIENTE",
            "destino_id": cid, "destino": destino,
        })

    print(f"\n=== CAMBIOS DE CLIENTE ({len(cambios)}) ===")
    for c in cambios:
        print(f"  {c['tiquete']}: {c['actual']!r} -> {c['destino']!r}")

    print(f"\n=== CAMBIOS DE NIT ({len(CLIENTES)}) ===")
    for cid, info in CLIENTES.items():
        c = con.execute("SELECT id, nombre, nit FROM cliente WHERE id = ?", (cid,)).fetchone()
        estado = "OK" if str(c["nit"] or "").strip() == info["nit"] else "actualizar {} -> {}".format(c["nit"], info["nit"])
        print(f"  {c['nombre']} (id {cid}): {estado}")

    if not ejecutar:
        print("\n[DRY-RUN] No se escribio nada. Usa --ejecutar para aplicar.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_clientes_validados_{ts}.db")
    shutil.copy2(DB_PATH, backup)
    print(f"\n[BACKUP] {backup}")

    con.execute("BEGIN")
    for c in cambios:
        con.execute("UPDATE llantas SET cliente_id = ? WHERE id = ?", (c["destino_id"], c["llanta_id"]))
    for cid, info in CLIENTES.items():
        con.execute("UPDATE cliente SET nit = ? WHERE id = ?", (info["nit"], cid))
    con.commit()
    print(f"[OK] Aplicadas {len(cambios)} asignaciones y {len(CLIENTES)} NITs.")


if __name__ == "__main__":
    main()