# -*- coding: utf-8 -*-
"""CorrecciÃ³n post-migraciÃ³n DELCA (v2.8.44/45) â€” alinear BD con el DBF fuente.

Orden del usuario:
  - NO tocar las 106 discrepancias "otras" (RECHAZADA forzadas + BD adelante).
  - NO tocar las ~21 llantas que solo existen en la BD.
  - Las demÃ¡s deben quedar iguales al DBF en: estado, ubicaciÃ³n y diseÃ±o.

Alcance (medido): 114 estado + 152 ubicaciÃ³n + 1,632 diseÃ±o = 1,898 llantas.

Proceso:
  1. Backup de delca.db (backups/migracion/delca_pre_correccion_*.db).
  2. Recalcula la clasificaciÃ³n (misma lÃ³gica de analisis_correccion.py).
  3. Crea el diseÃ±o faltante 'PBT14-W' (tipo MIXTO, convenciÃ³n de migraciÃ³n).
  4. UPDATE estado / ubicacion_actual / diseno_id donde difieran (solo FIX_*).
  5. Inserta auditorÃ­a en estados_llanta / ubicaciones_llanta (fecha = FECHA_SALI
     si >= fecha_ingreso, si no fecha_ingreso).
  6. Sincroniza fecha_salida/doc_salida cuando la llanta pasa a CLIENTE y el DBF
     trae FECHA_SALI (coherencia de la ubicaciÃ³n).
  7. Reporte + verificaciÃ³n.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime, time

from dbfread import DBF

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.dirname(PROJECT_ROOT)
DB = os.path.join(PROJECT_ROOT, "delca.db")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from scripts.migration_utils import backup_seguro
DBF_NUEVO = os.path.join(ORIGEN, "MAE_PROD.DBF")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups", "migracion")
TIPO_DISENO_DEFECTO = "MIXTO"

MAP_ESTADO = {"1": "REENCAUCHADA", "2": "APTA", "4": "REPARADA", "6": "PENDIENTE", "": "PENDIENTE"}
MAP_UBICACION = {"C": "CLIENTE", "B": "CLIENTE", "D": "CLIENTE", "E": "PRODUCCION", "P": "PLANTA"}


def fecha_dt(v):
    if isinstance(v, (date, datetime)):
        return datetime.combine(v, time.min) if not isinstance(v, datetime) else v
    return None


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # ---- 1. Backup ----
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_correccion_{ts}.db")
    backup_seguro(DB, backup)
    print(f"[BACKUP] {backup}")

    # ---- 2. Fuentes ----
    dbf = {}
    for r in DBF(DBF_NUEVO, encoding="cp1252"):
        tq2 = str(r["TIQUETE2"] or "").strip()
        if tq2:
            dbf[tq2] = {
                "est": str(r["ESTADO"] or "").strip(),
                "ubi": str(r["UBICACION"] or "").strip(),
                "banda": str(r["BANDA"] or "").strip(),
                "fecha_ent": fecha_dt(r["FECHA_ENT"]),
                "fecha_sal": fecha_dt(r["FECHA_SALI"]),
                "doc_sal": str(r["DOC_SALE"] or "").strip() or None,
            }
    print(f"[DBF] {len(dbf)} registros")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    disenos = {}
    for r in cur.execute("SELECT id, nombre, tipo FROM disenos_llanta"):
        disenos[(r["nombre"] or "").strip().upper()] = r["id"]
    print(f"[CATALOGO] {len(disenos)} disenos")

    # ---- 3. Crear diseÃ±o faltante 'PBT14-W' ----
    pendientes_crear = {r["banda"] for r in dbf.values() if r["banda"]}
    for banda in sorted(pendientes_crear):
        clave = banda.upper()
        if clave not in disenos:
            cur.execute("INSERT INTO disenos_llanta (nombre, tipo) VALUES (?, ?)", (banda, TIPO_DISENO_DEFECTO))
            disenos[clave] = cur.lastrowid
            print(f"[DISENO] creado: {banda} (id={cur.lastrowid}, tipo={TIPO_DISENO_DEFECTO})")
    con.commit()

    # ---- 4. ClasificaciÃ³n y aplicaciÃ³n ----
    stats = Counter()
    upd_estado = 0
    upd_ubicacion = 0
    upd_diseno = 0
    upd_fecha_salida = 0
    aud_estados = 0
    aud_ubicaciones = 0
    protegidas_check = 0

    for r in cur.execute("SELECT id, tiquete, estado, ubicacion_actual, diseno_id, fecha_ingreso, fecha_salida, doc_salida FROM llantas").fetchall():
        tq = str(r["tiquete"] or "").strip()
        rec = dbf.get(tq)
        if rec is None:
            stats["BD_ONLY"] += 1
            continue

        est_esp = MAP_ESTADO.get(rec["est"])
        ubi_esp = MAP_UBICACION.get(rec["ubi"])
        est_ok = (est_esp == (r["estado"] or "").strip())
        ubi_ok = (ubi_esp == (r["ubicacion_actual"] or "").strip())

        banda = rec["banda"]
        diseno_esp = disenos[banda.upper()] if banda else None
        diseno_ok = (diseno_esp == r["diseno_id"]) if diseno_esp is not None else True

        if est_ok and ubi_ok and diseno_ok:
            stats["OK"] += 1
            continue
        if r["estado"] == "PENDIENTE" and rec["est"] in ("1", "2", "4"):
            cls = "FIX_ESTADO"
        elif not est_ok:
            cls = "PROTEGIDA"
        elif not ubi_ok:
            cls = "FIX_UBICACION"
        else:
            cls = "FIX_DISENO"
        stats[cls] += 1

        if cls == "PROTEGIDA":
            protegidas_check += 1
            continue

        # --- Aplicar cambios ---
        nuevo_estado = est_esp if not est_ok else None
        nueva_ubi = ubi_esp if not ubi_ok else None
        nuevo_diseno = diseno_esp if (not diseno_ok and diseno_esp is not None) else None

        # fecha para auditorÃ­a: FECHA_SALI si existe y es >= ingreso (cuando saliÃ³
        # a CLIENTE), si no la fecha de la correcciÃ³n (cuando DELCA conoce el estado).
        fecha_aud = datetime.now()
        if rec["fecha_sal"] and (not rec["fecha_ent"] or rec["fecha_sal"] >= rec["fecha_ent"]):
            fecha_aud = rec["fecha_sal"]

        if nuevo_estado:
            cur.execute("UPDATE llantas SET estado=? WHERE id=?", (nuevo_estado, r["id"]))
            upd_estado += 1
            cur.execute("INSERT INTO estados_llanta (llanta_id, estado, fecha) VALUES (?,?,?)",
                        (r["id"], nuevo_estado, fecha_aud))
            aud_estados += 1

        if nueva_ubi:
            cur.execute("UPDATE llantas SET ubicacion_actual=? WHERE id=?", (nueva_ubi, r["id"]))
            upd_ubicacion += 1
            cur.execute("INSERT INTO ubicaciones_llanta (llanta_id, ubicacion, fecha) VALUES (?,?,?)",
                        (r["id"], nueva_ubi, fecha_aud))
            aud_ubicaciones += 1

        if nuevo_diseno:
            cur.execute("UPDATE llantas SET diseno_id=? WHERE id=?", (nuevo_diseno, r["id"]))
            upd_diseno += 1

        # fecha_salida/doc_salida coherentes al pasar a CLIENTE
        if nueva_ubi == "CLIENTE" and rec["fecha_sal"] and r["fecha_salida"] is None:
            cur.execute("UPDATE llantas SET fecha_salida=?, doc_salida=? WHERE id=?",
                        (rec["fecha_sal"], rec["doc_sal"], r["id"]))
            upd_fecha_salida += 1

    con.commit()

    # ---- 5. Reporte ----
    print()
    print("=" * 70)
    print("RESULTADO DE LA CORRECCION")
    print("=" * 70)
    for k in ("OK", "FIX_ESTADO", "FIX_UBICACION", "FIX_DISENO", "PROTEGIDA", "BD_ONLY"):
        print(f"  {k:15s} {stats[k]}")
    print(f"  Protegidas verificadas (no tocadas): {protegidas_check}")
    print()
    print(f"  UPDATEs estado:     {upd_estado}")
    print(f"  UPDATEs ubicacion:  {upd_ubicacion}")
    print(f"  UPDATEs diseno_id:  {upd_diseno}")
    print(f"  UPDATEs fecha_salida/doc_salida (a CLIENTE): {upd_fecha_salida}")
    print(f"  Auditoria estados_llanta insertados:  {aud_estados}")
    print(f"  Auditoria ubicaciones_llanta insertados: {aud_ubicaciones}")

    # ---- 6. VerificaciÃ³n inmediata ----
    print()
    print("=" * 70)
    print("VERIFICACION POST-CORRECCION")
    print("=" * 70)
    tot = cur.execute("SELECT COUNT(*) FROM llantas").fetchone()[0]
    print(f"  Total llantas: {tot}")
    for r in cur.execute("SELECT estado, COUNT(*) n FROM llantas GROUP BY estado ORDER BY n DESC"):
        print(f"    {r['estado']:15s} {r['n']}")

    con.close()
    print()
    print("CORRECCION APLICADA OK")


if __name__ == "__main__":
    main()