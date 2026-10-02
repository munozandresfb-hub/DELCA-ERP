# -*- coding: utf-8 -*-
"""Corrección de estados validada con el legacy (pantalla Producción) — 01/10/2026.

Regla CONFIRMADA por verificación manual del usuario en el legacy:
  - llanta PENDIENTE en DELCA con n_hist==1 y COD_INSPEC='1' en MAE_PROD 01/10
    -> el legacy la muestra APTA  ->  se actualiza a APTA (161 llantas)
  - COD_INSPEC='0' o '19'/'22'/'34' -> PENDIENTE real -> se mantiene
  - n_hist>=2 (procesadas en DELCA) -> se mantiene intacto
  - RECHAZADA (v2.8.45) -> se mantiene (orden previa)

Además inserta la llanta nueva 25498 (única del DBF 01/10 que no existe en DELCA).

Backup WAL-safe previo + auditoría en estados_llanta + verificación.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime, time

# ── sys.path: permitir `import scripts.migration_utils` ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dbfread import DBF

from scripts.migration_utils import backup_seguro

DB = os.path.join(PROJECT_ROOT, "delca.db")
DBF_PROD = os.path.join(os.path.dirname(PROJECT_ROOT), "Migracion 1-10", "MAE_PROD.DBF")
DBF_CLI = os.path.join(os.path.dirname(PROJECT_ROOT), "Migracion 1-10", "MAE_CLIENTE.DBF")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups", "migracion")


def norm_nit(s):
    import re
    return re.sub(r"[^0-9A-Za-z]", "", str(s).upper()) if s else ""


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # ── 1. Backup WAL-safe ──
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_estados_inspeccion_{ts}.db")
    backup_seguro(DB, backup)
    print(f"[BACKUP] {backup}")

    # ── 2. DBF 01/10: COD_INSPEC por tiquete ──
    dbf = {}
    for r in DBF(DBF_PROD, encoding="cp1252", ignore_missing_memofile=True):
        tq = str(r["TIQUETE2"] or "").strip()
        if tq:
            dbf[tq] = {
                "cod_inspec": str(r["COD_INSPEC"] or "").strip(),
                "est": str(r["ESTADO"] or "").strip(),
                "marca": str(r["COD_MARCA"] or "").strip(),
                "dim": str(r["DIMENSION"] or "").strip(),
                "banda": str(r["BANDA"] or "").strip(),
                "cod_cli": str(r["COD_CLIEN"] or "").strip(),
                "orden": str(r["ORDEN"] or "").strip(),
                "consec": str(r["CONSEC"] or "").strip(),
                "fecha_ent": r["FECHA_ENT"],
                "obs": str(r["OBSERVACIO"] or "").strip(),
            }
    print(f"[DBF] {len(dbf)} registros")

    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=5000")
    cur = con.cursor()

    # ── 3. PENDIENTE n_hist==1 con COD_INSPEC='1' -> APTA ──
    filas = cur.execute("""
        SELECT l.id, l.tiquete, l.estado, l.ubicacion_actual, l.fecha_ingreso
        FROM llantas l
        WHERE l.estado = 'PENDIENTE'
          AND (SELECT COUNT(*) FROM estados_llanta e WHERE e.llanta_id = l.id) = 1
    """).fetchall()
    print(f"[PENDIENTE n_hist=1] {len(filas)}")

    ahora = datetime.now()
    a_apta = []
    sin_dbf = []
    no_inspec = []
    for r in filas:
        info = dbf.get(str(r["tiquete"]).strip())
        if info is None:
            sin_dbf.append(r["tiquete"])
            continue
        if info["cod_inspec"] == "1":
            a_apta.append(r)
        else:
            no_inspec.append((r["tiquete"], info["cod_inspec"]))

    print(f"  -> COD_INSPEC='1' (APTA en legacy): {len(a_apta)}")
    print(f"  -> COD_INSPEC != '1' (quedan PENDIENTE): {len(no_inspec)}")
    print(f"  -> sin registro en DBF (BD-only, quedan): {len(sin_dbf)}")

    n_update = 0
    for r in a_apta:
        cur.execute("UPDATE llantas SET estado='APTA' WHERE id=?", (r["id"],))
        cur.execute("INSERT INTO estados_llanta (llanta_id, estado, fecha) VALUES (?,?,?)",
                    (r["id"], "APTA", ahora))
        n_update += 1
    print(f"[APLICADO] {n_update} llantas PENDIENTE -> APTA (auditoría @ {ahora})")

    # ── 4. Insertar la llanta nueva 25498 ──
    tq_nueva = "25498"
    rec = dbf.get(tq_nueva)
    if rec:
        existe = cur.execute("SELECT id FROM llantas WHERE tiquete=?", (tq_nueva,)).fetchone()
        if existe:
            print(f"[25498] ya existe, no se inserta")
        else:
            # catálogos
            marca = cur.execute("SELECT id, nombre FROM marcas_llanta WHERE siglas=?", (rec["marca"],)).fetchone()
            diseno = cur.execute("SELECT id FROM disenos_llanta WHERE nombre=?", (rec["banda"],)).fetchone()
            # dimension: parse 205/75R16 -> ancho 205, rin 16
            dim = cur.execute(
                "SELECT id FROM dimensiones_llanta WHERE ancho=205 AND rin=16 AND (perfil IS NULL OR perfil=75)"
            ).fetchone()
            # cliente por NIT (MAE_CLIENTE C3104)
            nits = {norm_nit(r2["nit"]): r2["id"] for r2 in cur.execute("SELECT id, nit FROM cliente")}
            cli_id = None
            for c in DBF(DBF_CLI, encoding="cp1252", ignore_missing_memofile=True):
                if str(c["COD_CLIEN"] or "").strip() == rec["cod_cli"]:
                    cli_id = nits.get(norm_nit(c["NIT_CLIEN"]))
                    break

            fecha_ing = datetime.combine(rec["fecha_ent"], time.min) if isinstance(rec["fecha_ent"], (date, datetime)) else None
            cur.execute(
                "INSERT INTO llantas (tiquete, numero_orden, consecutivo, marca, dimension, estado, ubicacion_actual, "
                "cliente_id, marca_id, dimension_id, diseno_id, precio_venta, fecha_ingreso, observaciones) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (tq_nueva, rec["orden"], rec["consec"],
                 marca["nombre"] if marca else rec["marca"],
                 rec["dim"], "PENDIENTE", "PLANTA",
                 cli_id, marca["id"] if marca else None,
                 dim["id"] if dim else None,
                 diseno["id"] if diseno else None,
                 1, fecha_ing, rec["obs"] or None),
            )
            llanta_id = cur.lastrowid
            cur.execute("INSERT INTO estados_llanta (llanta_id, estado, fecha) VALUES (?,?,?)",
                        (llanta_id, "PENDIENTE", fecha_ing or ahora))
            cur.execute("INSERT INTO ubicaciones_llanta (llanta_id, ubicacion, fecha) VALUES (?,?,?)",
                        (llanta_id, "PLANTA", fecha_ing or ahora))
            print(f"[25498] insertada (cliente_id={cli_id} marca={marca['nombre'] if marca else '?'} dim_id={dim['id'] if dim else '?'} diseno_id={diseno['id'] if diseno else '?'})")
    else:
        print("[25498] no está en DBF 01/10, omitida")

    con.commit()

    # ── 5. Verificación ──
    print()
    print("=" * 70)
    print("VERIFICACION POST-CORRECCION")
    print("=" * 70)
    print(f"  Integridad: {cur.execute('PRAGMA integrity_check').fetchone()[0]}")
    print("  Conteo por estado:")
    for r in cur.execute("SELECT estado, COUNT(*) n FROM llantas GROUP BY estado ORDER BY n DESC"):
        print(f"    {r['estado']:15s} {r['n']}")
    print("  Conteo por ubicacion:")
    for r in cur.execute("SELECT ubicacion_actual, COUNT(*) n FROM llantas GROUP BY ubicacion_actual ORDER BY n DESC"):
        print(f"    {r['ubicacion_actual']:15s} {r['n']}")
    print(f"  Total llantas: {cur.execute('SELECT COUNT(*) FROM llantas').fetchone()[0]}")
    existe_25498 = cur.execute("SELECT id, estado FROM llantas WHERE tiquete='25498'").fetchone()
    print(f"  25498 existe: {existe_25498 is not None}")
    con.close()
    print()
    print("CORRECCION APLICADA OK")


if __name__ == "__main__":
    main()