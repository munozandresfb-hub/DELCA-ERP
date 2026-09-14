# -*- coding: utf-8 -*-
"""Corrige el cliente de las llantas migradas desde MAE_PROD.DBF.

CAUSA RAIZ:
  El COD_CLIEN de MAE_CLIENTE.DBF es una CADENA ('98', 'C453', '5.236.034').
  La migracion original inserto los clientes en `cliente` SIN id explicito
  (SQLite asigno ids secuenciales 1..N) y las llantas se importaron copiando
  el cliente_id del CSV legacy (convertido a numero con corrimientos por
  bloque) -> desalineacion: llantas apuntando a clientes existentes pero
  equivocados.

SOLUCION (llave natural 100% confiable):
  llanta.tiquete -> MAE_PROD.COD_CLIEN -> MAE_CLIENTE.NIT_CLIEN -> cliente.id (por NIT).
  Verificado: NITs unicos en DELCA (0 duplicados), 0 ambiguedades, todos los
  NITs legacy existen en DELCA.

LECCION PARA FUTURAS MIGRACIONES:
  NUNCA confiar en ids autoincrementales del destino ni en numeros derivados
  del origen. Migrar SIEMPRE por llave natural (NIT/cedula/codigo unico) y
  verificar contra el origen tiquete a tiquete (o registro a registro).

Uso:
  python scripts/corregir_clientes_nit.py [--dry-run | --ejecutar]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
from datetime import datetime

from dbfread import DBF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "delca.db")
LEGACY_DIR = os.path.dirname(os.path.dirname(DB_PATH))  # carpeta DELCA con los .DBF
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

MAE_PROD_PATH = os.path.join(LEGACY_DIR, "MAE_PROD.DBF")
MAE_CLIENTE_PATH = os.path.join(LEGACY_DIR, "MAE_CLIENTE.DBF")


def norm_nit(s) -> str:
    if s is None:
        return ""
    return re.sub(r"[^0-9A-Za-z]", "", str(s).upper())


def cargar_mae_cliente():
    """COD_CLIEN -> (nit_normalizado, nombre, nit_bruto)"""
    mapa = {}
    cli = DBF(MAE_CLIENTE_PATH, encoding="cp1252")
    for r in cli:
        cod = str(r["COD_CLIEN"] or "").strip()
        mapa[cod] = (
            norm_nit(r["NIT_CLIEN"]),
            str(r["DESC_CLIEN"] or "").strip(),
            str(r["NIT_CLIEN"] or "").strip(),
        )
    return mapa


def cargar_mae_prod():
    """TIQUETE -> COD_CLIEN"""
    mapa = {}
    prod = DBF(MAE_PROD_PATH, encoding="cp1252")
    for r in prod:
        tq = str(r["TIQUETE"] or "").strip()
        mapa.setdefault(tq, str(r["COD_CLIEN"] or "").strip())
    return mapa


def main() -> None:
    parser = argparse.ArgumentParser(description="Corregir cliente de llantas por NIT (origen MAE_PROD.DBF)")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo simula (por defecto)")
    grupo.add_argument("--ejecutar", action="store_true", help="Aplica con backup previo")
    args = parser.parse_args()
    ejecutar = args.ejecutar

    if not os.path.exists(MAE_PROD_PATH) or not os.path.exists(MAE_CLIENTE_PATH):
        print(f"[ERROR] No se encuentran los DBF origen:\n  {MAE_PROD_PATH}\n  {MAE_CLIENTE_PATH}")
        return

    cli_map = cargar_mae_cliente()
    prod_map = cargar_mae_prod()
    print(f"[ORIGEN] MAE_CLIENTE: {len(cli_map)} | MAE_PROD: {len(prod_map)} tiquetes")

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # cliente DELCA: nit -> id (unico)
    nit2id = {}
    for c in con.execute("SELECT id, nit FROM cliente"):
        n = norm_nit(c["nit"])
        if n and n not in nit2id:
            nit2id[n] = c["id"]
    print(f"[BD] clientes con NIT unico: {len(nit2id)}")

    # Recolectar correcciones
    filas = con.execute(
        "SELECT id AS llanta_id, tiquete, cliente_id FROM llantas"
    ).fetchall()

    cambios: list[tuple[int, int]] = []   # (llanta_id, cliente_id_correcto)
    asignar_sin_cliente: list[tuple[int, int]] = []
    excepciones: list[dict] = []
    sin_codigo: int = 0

    for f in filas:
        tq = (f["tiquete"] or "").strip()
        cod = prod_map.get(tq, "")
        if cod not in cli_map:
            if f["cliente_id"] is None:
                sin_codigo += 1
            continue
        nit, nombre_legacy, nit_bruto = cli_map[cod]
        if not nit:
            excepciones.append({"tiquete": tq, "motivo": "NIT vacio en MAE_CLIENTE",
                                "nombre_legacy": nombre_legacy,
                                "nombre_actual": _nombre(con, f["cliente_id"])})
            continue
        id_correcto = nit2id.get(nit)
        if id_correcto is None:
            excepciones.append({"tiquete": tq, "motivo": "NIT no existe en DELCA",
                                "nombre_legacy": nombre_legacy, "nit": nit_bruto})
            continue
        if f["cliente_id"] is None:
            asignar_sin_cliente.append((f["llanta_id"], id_correcto))
        elif f["cliente_id"] != id_correcto:
            cambios.append((f["llanta_id"], id_correcto))

    print(f"\n[CAMBIOS] llantas con cliente incorrecto: {len(cambios)}")
    print(f"[SIN CLIENTE] llantas sin cliente (asignables): {len(asignar_sin_cliente)}")
    print(f"[EXCEPCIONES] con NIT vacio / no resuelto: {len(excepciones)}")
    if sin_codigo:
        print(f"[SIN CODIGO] llantas sin COD_CLIEN en MAE_PROD y sin cliente en BD: {sin_codigo}")

    if not ejecutar:
        print("\n[DRY-RUN] No se escribio nada. Usa --ejecutar para aplicar.")
        return

    # Backup
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_clientes_{ts}.db")
    shutil.copy2(DB_PATH, backup)
    print(f"[BACKUP] {backup}")

    con.execute("BEGIN")
    for llanta_id, cli_id in cambios:
        con.execute("UPDATE llantas SET cliente_id = ? WHERE id = ?", (cli_id, llanta_id))
    for llanta_id, cli_id in asignar_sin_cliente:
        con.execute("UPDATE llantas SET cliente_id = ? WHERE id = ?", (cli_id, llanta_id))
    con.commit()

    print(f"[OK] Corregidas {len(cambios)} + asignadas {len(asignar_sin_cliente)} llantas.")


def _nombre(con, cliente_id) -> str:
    if cliente_id is None:
        return ""
    r = con.execute("SELECT nombre FROM cliente WHERE id = ?", (cliente_id,)).fetchone()
    return r["nombre"] if r else ""


if __name__ == "__main__":
    main()