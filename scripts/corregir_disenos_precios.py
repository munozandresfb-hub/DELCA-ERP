# -*- coding: utf-8 -*-
"""Corrección de diseño y estados — alinea las llantas con el catálogo con precios.

Orden del usuario (01/10/2026):
  (a) tiquete 24922 -> REENCAUCHADA / CLIENTE
  (b) tiquete 25020 -> REPARADA / PLANTA
  (c) Migrar diseño de las llantas hacia los diseños CON precio en catálogo:
        DV-RT4(59) -> DVRT4(4)   [1,543 llantas]
        DV-RT2(60) -> DVRT2(3)   [146 llantas]
        PBT14-W(61) -> PBT14W(24) [13 llantas]
  (d) Eliminar diseños huérfanos sin referencias: 57, 58, 59, 60, 61
      (solo si 0 referencias en llantas/precios_producto/precios_venta_cliente/
       recetas_produccion/costos_produccion_estandar).

Backup WAL-safe previo + reporte + verificación.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date, datetime, time

# ── sys.path: permitir `import scripts.migration_utils` al ejecutar directo ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dbfread import DBF

from scripts.migration_utils import backup_seguro

DB = os.path.join(PROJECT_ROOT, "delca.db")
DBF_NUEVO = os.path.join(os.path.dirname(PROJECT_ROOT), "MAE_PROD.DBF")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups", "migracion")

# (a) y (b): correcciones de estado/ubicación puntuales
CORRECCIONES = {
    "24922": {"estado": "REENCAUCHADA", "ubicacion": "CLIENTE"},
    "25020": {"estado": "REPARADA", "ubicacion": "PLANTA"},
}

# (c): migración de diseño (diseno_id viejo -> nuevo)
MIGRACION_DISENO = {59: 4, 60: 3, 61: 24}

# (d): diseños candidatos a eliminar (solo si 0 referencias)
DISENOS_A_ELIMINAR = [57, 58, 59, 60, 61]
TABLAS_REF = ["llantas", "precios_producto", "precios_venta_cliente",
              "recetas_produccion", "costos_produccion_estandar"]


def _fecha_salida_dbf(tiquete: str):
    """Busca FECHA_SALI/FECHA_ENT en el DBF para el tiquete dado."""
    for r in DBF(DBF_NUEVO, encoding="cp1252"):
        if str(r["TIQUETE2"] or "").strip() == tiquete:
            sal = r["FECHA_SALI"]
            ent = r["FECHA_ENT"]
            fs = datetime.combine(sal, time.min) if isinstance(sal, (date, datetime)) else None
            fe = datetime.combine(ent, time.min) if isinstance(ent, (date, datetime)) else None
            return fs, fe
    return None, None


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # ── 1. Backup WAL-safe ──
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_disenos_{ts}.db")
    backup_seguro(DB, backup)
    print(f"[BACKUP] {backup}")

    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=5000")
    cur = con.cursor()

    # ── (a)+(b): estados/ubicaciones puntuales con auditoría ──
    for tq, cambios in CORRECCIONES.items():
        row = cur.execute("SELECT id, estado, ubicacion_actual, fecha_ingreso, fecha_salida FROM llantas WHERE tiquete=?", (tq,)).fetchone()
        if not row:
            print(f"[AVISO] {tq}: no existe, saltando")
            continue
        fecha_sal_dbf, fecha_ent_dbf = _fecha_salida_dbf(tq)
        fecha_aud = fecha_sal_dbf
        if fecha_aud is None or (fecha_ent_dbf and fecha_aud < fecha_ent_dbf):
            fecha_aud = fecha_ent_dbf or datetime.now()
        if fecha_aud is None:
            fecha_aud = datetime.now()

        if row["estado"] != cambios["estado"]:
            cur.execute("UPDATE llantas SET estado=? WHERE id=?", (cambios["estado"], row["id"]))
            cur.execute("INSERT INTO estados_llanta (llanta_id, estado, fecha) VALUES (?,?,?)",
                        (row["id"], cambios["estado"], fecha_aud))
            print(f"[ESTADO] {tq}: {row['estado']} -> {cambios['estado']} (auditoría @ {fecha_aud})")
        if row["ubicacion_actual"] != cambios["ubicacion"]:
            cur.execute("UPDATE llantas SET ubicacion_actual=? WHERE id=?", (cambios["ubicacion"], row["id"]))
            cur.execute("INSERT INTO ubicaciones_llanta (llanta_id, ubicacion, fecha) VALUES (?,?,?)",
                        (row["id"], cambios["ubicacion"], fecha_aud))
            print(f"[UBICACION] {tq}: {row['ubicacion_actual']} -> {cambios['ubicacion']}")

    # ── (c): migración de diseño ──
    for viejo, nuevo in MIGRACION_DISENO.items():
        n = cur.execute("UPDATE llantas SET diseno_id=? WHERE diseno_id=?", (nuevo, viejo)).rowcount
        print(f"[DISENO] {viejo} -> {nuevo}: {n} llantas migradas")

    # ── (d): eliminar diseños huérfanos ──
    for did in DISENOS_A_ELIMINAR:
        refs = []
        for tabla in TABLAS_REF:
            try:
                cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tabla})")]
                if "diseno_id" not in cols:
                    continue
                n = cur.execute(f"SELECT COUNT(*) FROM {tabla} WHERE diseno_id=?", (did,)).fetchone()[0]
                if n:
                    refs.append(f"{tabla}={n}")
            except sqlite3.Error:
                pass
        if refs:
            print(f"[ELIMINAR] diseno {did}: NO eliminado (referencias: {refs})")
        else:
            cur.execute("DELETE FROM disenos_llanta WHERE id=?", (did,))
            print(f"[ELIMINAR] diseno {did}: eliminado")

    con.commit()

    # ── Verificación ──
    print()
    print("=" * 70)
    print("VERIFICACION POST-CORRECCION")
    print("=" * 70)
    print(f"  Integridad: {cur.execute('PRAGMA integrity_check').fetchone()[0]}")
    for r in cur.execute("SELECT estado, COUNT(*) n FROM llantas GROUP BY estado ORDER BY n DESC"):
        print(f"    estado {r['estado']:15s} {r['n']}")
    print(f"  diseno_id 3 (DVRT2): {cur.execute('SELECT COUNT(*) FROM llantas WHERE diseno_id=3').fetchone()[0]}")
    print(f"  diseno_id 4 (DVRT4): {cur.execute('SELECT COUNT(*) FROM llantas WHERE diseno_id=4').fetchone()[0]}")
    print(f"  diseno_id 24 (PBT14W): {cur.execute('SELECT COUNT(*) FROM llantas WHERE diseno_id=24').fetchone()[0]}")
    print(f"  disenos 57-61 en catalogo: {cur.execute('SELECT COUNT(*) FROM disenos_llanta WHERE id IN (57,58,59,60,61)').fetchone()[0]}")
    con.close()
    print()
    print("CORRECCION APLICADA OK")


if __name__ == "__main__":
    main()