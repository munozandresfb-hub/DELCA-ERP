# -*- coding: utf-8 -*-
"""Migración v2.8.44 — Re-migración de datos nuevos desde MAE_PROD/MAE_CLIENTE/MAE_MARCA.

Agrega a DELCA las llantas y clientes que aún no existen (universo completo en
los DBF: los registros ya migrados se saltan por TIQUETE2 / NIT).

Reglas (mapeo exacto validado contra la BD):
  - Tiquete = TIQUETE2 (sin la "J"; el impreso en la llanta).
  - ESTADO: '1'->REENCAUCHADA, '2'->APTA, '4'->REPARADA, '6'/vacío->PENDIENTE.
  - UBICACION: C/B/D->CLIENTE, E->PRODUCCION, P->PLANTA.
  - Combinaciones inválidas R1-R6 -> no migran (CSV "llantas no migradas.csv").
  - Cliente por NIT (crea los clientes nuevos del MAE_CLIENTE).
  - Marca/dimensión/diseño resueltos contra catálogos (crea faltantes parseables).
  - Costo/precio desde precios_producto (sin cobertura -> precio 1).
  - Historiales iniciales (estado + ubicación) con la fecha de ingreso real.

Uso: python scripts/migrar_remigracion_dbf.py
(requiere los DBF nuevos en C:\\Users\\andre\\OneDrive\\Escritorio\\DELCA\\)
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

ORIGEN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "delca.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups", "migracion")
CSV_RECHAZADAS = os.path.join(ORIGEN, "llantas no migradas.csv")

MAP_ESTADO = {"1": "REENCAUCHADA", "2": "APTA", "4": "REPARADA", "6": "PENDIENTE", "": "PENDIENTE"}
MAP_UBICACION = {"C": "CLIENTE", "B": "CLIENTE", "D": "CLIENTE", "E": "PRODUCCION", "P": "PLANTA"}
COMBINACIONES = {
    "PENDIENTE": {"PLANTA"}, "APTA": {"PRODUCCION", "PLANTA"},
    "RECHAZADA": {"PLANTA", "CLIENTE"}, "REENCAUCHADA": {"PLANTA", "CLIENTE"},
    "REPARADA": {"PLANTA", "CLIENTE"}, "REPROCESO": {"PRODUCCION"},
}
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
    backup = os.path.join(BACKUP_DIR, f"delca_pre_remigracion_{ts}.db")
    shutil.copy2(DB, backup)
    print(f"[BACKUP] {backup}")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    clientes = DBF(os.path.join(ORIGEN, "MAE_CLIENTE.DBF"), encoding="cp1252")
    nits_bd = {norm_nit(r["nit"]) for r in cur.execute("SELECT nit FROM cliente")}
    clientes_creados = 0
    clientes_cod_nit = {}
    for r in clientes:
        nit = norm_nit(r["NIT_CLIEN"])
        cod = str(r["COD_CLIEN"] or "").strip()
        if nit:
            clientes_cod_nit[cod] = nit
        if nit and nit not in nits_bd:
            cur.execute(
                "INSERT INTO cliente (nombre, nit, telefono, celular, email, direccion, ciudad, saldo, activo, categoria_abc) "
                "VALUES (?,?,?,?,?,?,?,0,1,NULL)",
                (str(r["DESC_CLIEN"] or "").strip(), str(r["NIT_CLIEN"] or "").strip(),
                 str(r["TEL_CLIEN"] or "").strip() or None, None,
                 str(r["MAIL_CLIEN"] or "").strip() or None,
                 str(r["DIREC_CLIE"] or "").strip() or None, None),
            )
            nits_bd.add(nit)
            clientes_creados += 1
    print(f"[CLIENTES] creados nuevos: {clientes_creados}")

    nit_id = {norm_nit(r["nit"]): r["id"] for r in cur.execute("SELECT id, nit FROM cliente").fetchall()}

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
    prod = DBF(os.path.join(ORIGEN, "MAE_PROD.DBF"), encoding="cp1252")

    insertadas = 0
    sin_cliente = 0
    sin_marca = 0
    dim_creadas = 0
    diseno_creados = 0
    rechazadas = []
    sin_tiquete2 = 0

    for r in prod:
        tq2 = str(r["TIQUETE2"] or "").strip()
        if not tq2:
            sin_tiquete2 += 1
            continue
        if tq2 in tiquetes_bd:
            continue
        est = MAP_ESTADO.get(str(r["ESTADO"] or "").strip(), "PENDIENTE")
        ubi = MAP_UBICACION.get(str(r["UBICACION"] or "").strip(), None)
        if ubi is None or ubi not in COMBINACIONES.get(est, set()):
            rechazadas.append({
                "tiquete": tq2, "estado_legacy": str(r["ESTADO"] or "").strip(),
                "ubicacion_legacy": str(r["UBICACION"] or "").strip(),
                "motivo": "combinacion invalida R1-R6",
            })
            continue

        cliente_id = None
        nit = clientes_cod_nit.get(str(r["COD_CLIEN"] or "").strip())
        if nit and nit in nit_id:
            cliente_id = nit_id[nit]
        if cliente_id is None:
            sin_cliente += 1

        marca_id_v = None
        cod_mar = str(r["COD_MARCA"] or "").strip().upper()
        if cod_mar in marca_id:
            marca_id_v = marca_id[cod_mar]
        else:
            sin_marca += 1

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
                dim_creadas += 1

        diseno_id_v = None
        banda = str(r["BANDA"] or "").strip()
        if banda:
            clave_d = banda.upper()
            if clave_d in diseno_id:
                diseno_id_v = diseno_id[clave_d]
            else:
                cur.execute("INSERT INTO disenos_llanta (nombre, tipo) VALUES (?, ?)",
                            (banda, TIPO_DISENO_DEFECTO))
                diseno_id_v = cur.lastrowid
                diseno_id[clave_d] = diseno_id_v
                diseno_creados += 1

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
             marca_texto, str(r["DIMENSION"] or "").strip() or None, est, ubi,
             cliente_id, marca_id_v, dim_id_v, diseno_id_v, costo, precio,
             fecha_ing, fecha_salida, doc_sale,
             str(r["OBSERVACIO"] or "").strip() or None),
        )
        llanta_id = cur.lastrowid
        cur.execute("INSERT INTO estados_llanta (llanta_id, estado, fecha) VALUES (?,?,?)",
                    (llanta_id, est, fecha_ing))
        cur.execute("INSERT INTO ubicaciones_llanta (llanta_id, ubicacion, fecha) VALUES (?,?,?)",
                    (llanta_id, ubi, fecha_ing))
        tiquetes_bd.add(tq2)
        insertadas += 1

    con.commit()

    with open(CSV_RECHAZADAS, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["tiquete", "estado_legacy", "ubicacion_legacy", "motivo"])
        w.writeheader()
        w.writerows(rechazadas)

    print(f"\n=== REPORTE FINAL ===")
    print(f"  Backup: {backup}")
    print(f"  Clientes nuevos creados: {clientes_creados}")
    print(f"  Llantas nuevas importadas: {insertadas}")
    print(f"  Sin cliente (NULL): {sin_cliente}")
    print(f"  Sin marca en catalogo (NULL): {sin_marca}")
    print(f"  Dimensiones creadas: {dim_creadas}")
    print(f"  Disenos creados (tipo {TIPO_DISENO_DEFECTO}): {diseno_creados}")
    print(f"  Rechazadas (R1-R6) -> CSV: {len(rechazadas)}")
    print(f"  Sin TIQUETE2 (omitidas): {sin_tiquete2}")
    con.close()
    print(f"  CSV rechazadas: {CSV_RECHAZADAS}")
    print("MIGRACION APLICADA OK")


if __name__ == "__main__":
    main()