# -*- coding: utf-8 -*-
"""Corrige el tiquete de las llantas migradas (campo equivocado: TIQUETE vs TIQUETE2).

CAUSA RAIZ:
  El sistema legacy (MAE_PROD.DBF) almacena por llanta DOS campos de tiquete:
    - TIQUETE  ('J1353'): numero de secuencia interna del registro (con prefijo J)
    - TIQUETE2 ('1355'):  el TIQUETE REAL, el que esta impreso en la llanta fisica
  La migracion original guardo TIQUETE (con J) como tiquete -> el programa nuevo
  mostraba numeros que NO coinciden con las llantas fisicas ni con el programa
  origen. Verificado: O.S. 577-1 corresponde al tiquete 1355 (TIQUETE2), no 1353.

SOLUCION:
  llanta.tiquete (actual, 'J1353') -> TIQUETE2 del MAE_PROD ('1355').
  TIQUETE2 es unico (0 duplicados) y no tiene prefijo J -> se guarda tal cual.
  Excepcion: J23489 no tiene TIQUETE2 en el MAE_PROD (se deja sin tocar).

LECCION PARA FUTURAS MIGRACIONES:
  Verificar SIEMPRE el tiquete/identificador contra el valor IMPRESO en el
  articulo fisico (o contra el programa origen), no contra el primer campo
  con nombre similar del DBF. Los sistemas legacy suelen tener campos de
  secuencia interna junto al identificador real.

Uso: python scripts/corregir_tiquetes.py [--dry-run | --ejecutar]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
from datetime import datetime

from dbfread import DBF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "delca.db")
LEGACY_DIR = os.path.dirname(os.path.dirname(DB_PATH))  # carpeta DELCA (padre del proyecto)
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

MAE_PROD_PATH = os.path.join(LEGACY_DIR, "MAE_PROD.DBF")


def main() -> None:
    parser = argparse.ArgumentParser(description="Corregir tiquete de llantas (TIQUETE -> TIQUETE2 del MAE_PROD)")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo simula (por defecto)")
    grupo.add_argument("--ejecutar", action="store_true", help="Aplica con backup previo")
    args = parser.parse_args()
    ejecutar = args.ejecutar

    if not os.path.exists(MAE_PROD_PATH):
        print(f"[ERROR] No se encuentra {MAE_PROD_PATH}")
        return

    # 1) MAE_PROD: TIQUETE -> TIQUETE2
    tiquete2_map = {}
    prod = DBF(MAE_PROD_PATH, encoding="cp1252")
    for r in prod:
        t = str(r["TIQUETE"] or "").strip()
        t2 = str(r["TIQUETE2"] or "").strip()
        if t and t2:
            tiquete2_map[t] = t2
    print(f"[ORIGEN] MAE_PROD: {len(tiquete2_map)} llantas con TIQUETE2")

    # 2) BD
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    llantas = con.execute("SELECT id, tiquete FROM llantas").fetchall()

    cambios = []
    excepciones = []
    for l in llantas:
        t = (l["tiquete"] or "").strip()
        t2 = tiquete2_map.get(t)
        if t2 is None:
            excepciones.append({"id": l["id"], "tiquete": t, "motivo": "sin TIQUETE2 en MAE_PROD"})
        elif t2 != t:
            cambios.append({"id": l["id"], "tiquete_actual": t, "tiquete_nuevo": t2})

    print(f"[BD] llantas: {len(llantas)}")
    print(f"[CAMBIOS] tiquetes a corregir: {len(cambios)}")
    print(f"[EXCEPCIONES] sin TIQUETE2: {len(excepciones)}")
    for e in excepciones:
        print(f"    {e['tiquete']} ({e['motivo']})")

    # unicidad final
    nuevos = [c["tiquete_nuevo"] for c in cambios]
    duplicados = {n for n in nuevos if nuevos.count(n) > 1}
    print(f"[UNICIDAD] nuevos tiquetes unicos: {len(set(nuevos))} | duplicados: {len(duplicados)}")
    if duplicados:
        print(f"    DUPLICADOS: {list(duplicados)[:10]}")

    print("\n=== Ejemplos de correccion ===")
    for c in cambios[:10]:
        print(f"    {c['tiquete_actual']} -> {c['tiquete_nuevo']}")

    if not ejecutar:
        print("\n[DRY-RUN] No se escribio nada. Usa --ejecutar para aplicar.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_tiquetes_{ts}.db")
    shutil.copy2(DB_PATH, backup)
    print(f"[BACKUP] {backup}")

    con.execute("BEGIN")
    for c in cambios:
        con.execute("UPDATE llantas SET tiquete = ? WHERE id = ?", (c["tiquete_nuevo"], c["id"]))
    con.commit()
    print(f"[OK] Corregidos {len(cambios)} tiquetes. Excepciones sin tocar: {len(excepciones)}")


if __name__ == "__main__":
    main()