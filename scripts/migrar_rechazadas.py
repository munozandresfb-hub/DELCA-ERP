# -*- coding: utf-8 -*-
"""Migra las llantas RECHAZADAS de la re-migraciÃ³n (v2.8.45) con tratamiento especial.

Lee 'llantas no migradas.csv' (generado por migrar_remigracion_dbf.py) e inserta
cada llanta terminando en estado RECHAZADA / ubicaciÃ³n CLIENTE (vÃ¡lido):
  - Las 67 con ubicaciÃ³n legacy E (PRODUCCION): historial PLANTA -> RECHAZADA -> CLIENTE
  - Las 12 con ubicaciÃ³n legacy C (CLIENTE): estado RECHAZADA conservando CLIENTE

Requiere los DBF en C:\\Users\\andre\\OneDrive\\Escritorio\\DELCA\\
Uso: python scripts/migrar_rechazadas.py
"""
from __future__ import annotations

import csv
import os
import re
import shutil
import sqlite3
import sys
from datetime import date, datetime, time

from dbfread import DBF

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.dirname(PROJECT_ROOT)
DB = os.path.join(PROJECT_ROOT, "delca.db")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups", "migracion")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from scripts.migration_utils import backup_seguro
CSV_PATH = os.path.join(ORIGEN, "llantas no migradas.csv")
TIPO_DISENO_DEFECTO = "MIXTO"


def norm_nit(s):
    return re.sub(r"[^0-9A-Za-z]", "", str(s).upper()) if s else ""


def parse_dim(dim):
    d = (dim or "").strip()
    if not d:
        return None
    m_suf = re.search(r"([A-Za-z]+)$", d)
    sufijo = ""
    cuerpo = d
    if m_suf:
        sufijo = m_suf.group(1)
        cuerpo = d[:m_suf.start()].strip()
    m = re.match(r"^(\d+(?:\.\d+)?)(?:/(\d{2}))?\s*[Rr]\s*(\d+(?:\.\d+)?)$", cuerpo)
    if m:
        return float(m.group(1)), (int(m.group(2)) if m.group(2) else None), float(m.group(3)), sufijo
    m1b = re.match(r"^(\d+(?:\.\d+)?)/(\d{2})\s*[-]\s*(\d+(?:\.\d+)?)$", cuerpo)
    if m1b:
        return float(m1b.group(1)), int(m1b.group(2)), float(m1b.group(3)), sufijo
    m2 = re.match(r"^(\d+\.?\d*)[\s\-/](\d+\.?\d*)$", cuerpo)
    if m2:
        return float(m2.group(1)), None, float(m2.group(2)), sufijo
    m3 = re.match(r"^(\d{2})[Xx](\d+\.?\d*)[Rr](\d+(?:\.\d+)?)$", cuerpo)
    if m3:
        return float(m3.group(2)), None, float(m3.group(3)), sufijo
    m4 = re.match(r"^[A-Za-z]\d{2}[\s\-/](\d+(?:\.\d+)?)$", cuerpo)
    if m4:
        return None, None, float(m4.group(1)), sufijo
    return None


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_rechazadas_{ts}.db")
    backup_seguro(DB, backup)
    print(f"[BACKUP] {backup}")

    rechazadas = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rechazadas.append(r)
    print(f"[CSV] {len(rechazadas)} llantas rechazadas")

    prod = DBF(os.path.join(ORIGEN, "MAE_PROD.DBF"), encoding="cp1252")
    indice = {str(r["TIQUETE2"] or "").strip(): r for r in prod}

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    nit_id = {norm_nit(r["nit"]): r["id"] for r in cur.execute("SELECT id, nit FROM cliente")}
    clientes_cod_nit = {}
    for r in DBF(os.path.join(ORIGEN, "MAE_CLIENTE.DBF"), encoding="cp1252"):
        cod = str(r["COD_CLIEN"] or "").strip()
        nit = norm_nit(r["NIT_CLIEN"])
        if cod and nit:
            clientes_cod_nit[cod] = nit

    marca_id = {}
    for r in cur.execute("SELECT id, siglas FROM marcas_llanta").fetchall():
        sig = (r["siglas"] or "").strip().upper()
        if sig:
            marca_id[sig] = r["id"]
    dim_id = {}
    for r in cur.execute("SELECT id, ancho, rin FROM dimensiones_llanta").fetchall():
        dim_id[(r["ancho"], r["rin"])] = r["id"]
    diseno_id = {}
    for r in cur.execute("SELECT id, nombre FROM disenos_llanta").fetchall():
        diseno_id[(r["nombre"] or "").strip().upper()] = r["id"]
    precios = {}
    for r in cur.execute("SELECT dimension_id, diseno_id, costo_fabricacion, precio_minimo, precio_normal FROM precios_producto").fetchall():
        precios[(r["dimension_id"], r["diseno_id"])] = (r["costo_fabricacion"], r["precio_minimo"], r["precio_normal"])

    tiquetes_bd = {r["tiquete"] for r in cur.execute("SELECT tiquete FROM llantas WHERE tiquete IS NOT NULL")}
    hoy = datetime.now()

    insertadas = 0
    ya_existian = 0
    sin_registro_dbf = 0

    for rec in rechazadas:
        tq2 = rec["tiquete"].strip()
        if tq2 in tiquetes_bd:
            ya_existian += 1
            continue
        r = indice.get(tq2)
        if not r:
            sin_registro_dbf += 1
            continue
        es_e = rec["ubicacion_legacy"].strip().upper() == "E"

        cliente_id = None
        nit = clientes_cod_nit.get(str(r["COD_CLIEN"] or "").strip())
        if nit and nit in nit_id:
            cliente_id = nit_id[nit]
        marca_id_v = marca_id.get(str(r["COD_MARCA"] or "").strip().upper())

        dim_id_v = None
        pd = parse_dim(str(r["DIMENSION"] or "").strip())
        if pd:
            ancho, perfil, rin, sufijo = pd
            clave = (ancho, rin)
            if clave in dim_id:
                dim_id_v = dim_id[clave]
            else:
                cur.execute("INSERT INTO dimensiones_llanta (ancho, perfil, rin, sufijo) VALUES (?,?,?,?)",
                            (ancho, perfil, rin, sufijo))
                dim_id_v = cur.lastrowid
                dim_id[clave] = dim_id_v

        diseno_id_v = None
        banda = str(r["BANDA"] or "").strip()
        if banda:
            clave_d = banda.upper()
            if clave_d in diseno_id:
                diseno_id_v = diseno_id[clave_d]
            else:
                cur.execute("INSERT INTO disenos_llanta (nombre, tipo) VALUES (?, ?)", (banda, TIPO_DISENO_DEFECTO))
                diseno_id_v = cur.lastrowid
                diseno_id[clave_d] = diseno_id_v

        costo = None
        precio = None
        pp = precios.get((dim_id_v, diseno_id_v))
        if pp:
            costo = pp[0]
            precio = pp[2] if pp[2] else (pp[1] if pp[1] else 1)
        else:
            precio = 1

        fecha_ent = r["FECHA_ENT"]
        fecha_ing = datetime.combine(fecha_ent, time.min) if isinstance(fecha_ent, (date, datetime)) else None
        fecha_sal = r["FECHA_SALI"]
        fecha_salida = datetime.combine(fecha_sal, time.min) if isinstance(fecha_sal, (date, datetime)) else None
        doc_sale = str(r["DOC_SALE"] or "").strip() or None

        marca_texto = None
        m_nombre = cur.execute("SELECT nombre FROM marcas_llanta WHERE id=?", (marca_id_v,)).fetchone() if marca_id_v else None
        if m_nombre:
            marca_texto = m_nombre["nombre"]

        cur.execute(
            "INSERT INTO llantas (tiquete, numero_orden, consecutivo, marca, dimension, estado, ubicacion_actual, "
            "cliente_id, marca_id, dimension_id, diseno_id, costo_produccion, precio_venta, "
            "fecha_ingreso, fecha_salida, doc_salida, observaciones) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tq2, str(r["ORDEN"] or "").strip() or None, str(r["CONSEC"] or "").strip() or None,
             marca_texto, str(r["DIMENSION"] or "").strip() or None, "RECHAZADA", "CLIENTE",
             cliente_id, marca_id_v, dim_id_v, diseno_id_v, costo, precio,
             fecha_ing, fecha_salida, doc_sale,
             str(r["OBSERVACIO"] or "").strip() or None),
        )
        llanta_id = cur.lastrowid

        if es_e:
            cur.execute("INSERT INTO ubicaciones_llanta (llanta_id, ubicacion, fecha) VALUES (?,?,?)",
                        (llanta_id, "PLANTA", fecha_ing))
            cur.execute("INSERT INTO estados_llanta (llanta_id, estado, fecha) VALUES (?,?,?)",
                        (llanta_id, "RECHAZADA", hoy))
            cur.execute("INSERT INTO ubicaciones_llanta (llanta_id, ubicacion, fecha) VALUES (?,?,?)",
                        (llanta_id, "CLIENTE", hoy))
        else:
            cur.execute("INSERT INTO estados_llanta (llanta_id, estado, fecha) VALUES (?,?,?)",
                        (llanta_id, "RECHAZADA", fecha_ing or hoy))
            cur.execute("INSERT INTO ubicaciones_llanta (llanta_id, ubicacion, fecha) VALUES (?,?,?)",
                        (llanta_id, "CLIENTE", fecha_ing or hoy))

        tiquetes_bd.add(tq2)
        insertadas += 1

    con.commit()
    print(f"\n=== REPORTE ===")
    print(f"  Insertadas (RECHAZADA / CLIENTE): {insertadas}")
    print(f"  Ya existian (saltadas): {ya_existian}")
    print(f"  Sin registro en DBF: {sin_registro_dbf}")
    print("  Nota: causa_rechazo_id queda NULL (criterio de RECHAZADAS legacy)")
    con.close()
    print("APLICADO OK")


if __name__ == "__main__":
    main()