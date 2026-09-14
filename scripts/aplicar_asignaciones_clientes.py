# -*- coding: utf-8 -*-
"""Aplica las 18 asignaciones de cliente validadas por el negocio (2026-09-14).

Estas 18 llantas tienen el NIT vacio en MAE_CLIENTE (no verificables por NIT).
La validacion manual del negocio determino el cliente correcto por nombre.

Asignaciones (tiquetes -> cliente_id):
  ROSELLANTAS LTDA (DIST)  id 491: J1353, J1354
  ROBERTO LOPEZ            id 675: J6106, J13298
  GIRALDO RIVERA           id 672: J7165, J7166, J7167
  PEREZ ABELINO            id 506: J11917, J11918
  GERARDO BRAVO            id 431: J13226, J19334, J19335, J22961, J22962
  TORO JOSE DOMINGO        id 532: J13997, J14402, J14669, J17441

Uso: python scripts/aplicar_asignaciones_clientes.py [--dry-run | --ejecutar]
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

ASIGNACIONES = {
    "J1353": 491, "J1354": 491,
    "J6106": 675, "J13298": 675,
    "J7165": 672, "J7166": 672, "J7167": 672,
    "J11917": 506, "J11918": 506,
    "J13226": 431, "J19334": 431, "J19335": 431, "J22961": 431, "J22962": 431,
    "J13997": 532, "J14402": 532, "J14669": 532, "J17441": 532,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplicar 18 asignaciones de cliente validadas")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo simula (por defecto)")
    grupo.add_argument("--ejecutar", action="store_true", help="Aplica con backup")
    args = parser.parse_args()
    ejecutar = args.ejecutar

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print(f"Asignaciones definidas: {len(ASIGNACIONES)} llantas")
    cambios = []
    no_encontradas = []
    for tq, id_destino in sorted(ASIGNACIONES.items()):
        r = con.execute("SELECT id, tiquete, cliente_id FROM llantas WHERE tiquete = ?", (tq,)).fetchone()
        if not r:
            no_encontradas.append(tq)
            continue
        actual = con.execute("SELECT nombre FROM cliente WHERE id = ?", (r["cliente_id"],)).fetchone() if r["cliente_id"] else None
        destino = con.execute("SELECT nombre FROM cliente WHERE id = ?", (id_destino,)).fetchone()
        cambios.append({
            "llanta_id": r["id"], "tiquete": tq,
            "cliente_actual_id": r["cliente_id"],
            "cliente_actual": actual["nombre"] if actual else "SIN CLIENTE",
            "cliente_destino_id": id_destino,
            "cliente_destino": destino["nombre"] if destino else "??NO EXISTE??",
        })

    print(f"\nLlantas encontradas: {len(cambios)} | no encontradas: {len(no_encontradas)}")
    for c in cambios:
        print(f"  {c['tiquete']}: {c['cliente_actual']!r} (id {c['cliente_actual_id']}) -> {c['cliente_destino']!r} (id {c['cliente_destino_id']})")
    if no_encontradas:
        print(f"  NO ENCONTRADAS: {no_encontradas}")

    # Validar que los destinos existen
    destinos_rotos = [c for c in cambios if "NO EXISTE" in c["cliente_destino"]]
    if destinos_rotos:
        print(f"\n[ERROR] Hay {len(destinos_rotos)} destinos inexistentes. Abortando.")
        return

    if not ejecutar:
        print("\n[DRY-RUN] No se escribio nada. Usa --ejecutar para aplicar.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_asignaciones18_{ts}.db")
    shutil.copy2(DB_PATH, backup)
    print(f"[BACKUP] {backup}")

    con.execute("BEGIN")
    for c in cambios:
        con.execute("UPDATE llantas SET cliente_id = ? WHERE id = ?", (c["cliente_destino_id"], c["llanta_id"]))
    con.commit()
    print(f"[OK] Aplicadas {len(cambios)} asignaciones.")


if __name__ == "__main__":
    main()