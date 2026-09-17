# -*- coding: utf-8 -*-
"""Unifica dimensiones de llantas (indicación del negocio, 2026-09-16).

Unificaciones (se conservan las llantas, solo cambia dimension_id):
  95R17.5 (ancho 95, rin 17.5)  -> 9.5R17.5 (ancho 9.5, rin 17.5)   [conserva precios 9.5R17.5]
  7R15    (ancho 7,  rin 15)    -> 700R15 (ancho 700, rin 15)        [conserva precios 700R15]
  7R16    (ancho 7,  rin 16)    -> 700R16 (ancho 700, rin 16)        [SE CREA la dimensión]

Catálogo (precios_producto) por (dimensión + diseño):
  - Combinación que YA existe en la dimensión destino -> se elimina la de la vieja
    (el destino conserva SUS precios).
  - Combinación SIN equivalente en el destino -> se MUEVE a la destino con SUS precios
    (evita llantas sin cobertura).
  - Las dimensiones viejas se eliminan de dimensiones_llanta (quedan sin referencias).

Uso: python scripts/unificar_dimensiones.py [--dry-run | --ejecutar]
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

# (ancho, rin) origen -> (ancho, rin) destino
UNIFICACIONES = [
    (("95.0", "17.5"), ("9.5", "17.5")),   # 95R17.5 -> 9.5R17.5
    (("7.0", "15.0"), ("700.0", "15.0")),  # 7R15 -> 700R15
    (("7.0", "16.0"), ("700.0", "16.0")),  # 7R16 -> 700R16 (crear destino)
]


def _dim_id(con, ancho, rin) -> int | None:
    r = con.execute(
        "SELECT id FROM dimensiones_llanta WHERE ancho = ? AND rin = ?",
        (float(ancho), float(rin)),
    ).fetchone()
    return r[0] if r else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Unificar dimensiones de llantas")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo simula (por defecto)")
    grupo.add_argument("--ejecutar", action="store_true", help="Aplica con backup")
    args = parser.parse_args()
    ejecutar = args.ejecutar

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    plan = []
    for (a_ori, r_ori), (a_des, r_des) in UNIFICACIONES:
        id_ori = _dim_id(con, a_ori, r_ori)
        id_des = _dim_id(con, a_des, r_des)
        crear_des = id_des is None
        nombre = "{}R{} -> {}R{}".format(a_ori.replace(".0", ""), r_ori.replace(".0", ""),
                                          a_des.replace(".0", ""), r_des.replace(".0", ""))
        if id_ori is None:
            print("[SKIP] {}: dimensión origen no existe".format(nombre))
            continue
        n_ll = con.execute("SELECT COUNT(*) FROM llantas WHERE dimension_id=?", (id_ori,)).fetchone()[0]
        refs = con.execute("SELECT p.id, p.diseno_id FROM precios_producto p WHERE p.dimension_id=?", (id_ori,)).fetchall()
        plan.append({
            "nombre": nombre, "id_ori": id_ori, "id_des": id_des, "crear_des": crear_des,
            "a_des": a_des, "r_des": r_des, "llantas": n_ll, "refs": [r["id"] for r in refs],
        })
        print("[PLAN] {}: {} llantas | {} refs catálogo | destino {}".format(
            nombre, n_ll, len(refs), "CREAR" if crear_des else "id={}".format(id_des)))

        # Clasificar refs: eliminar (existe en destino) vs mover (sin equivalente)
        for r in refs:
            existe = False
            if id_des:
                existe = con.execute(
                    "SELECT 1 FROM precios_producto WHERE dimension_id=? AND diseno_id=?",
                    (id_des, r["diseno_id"]),
                ).fetchone() is not None
            accion = "ELIMINAR (destino conserva su precio)" if existe else "MOVER con sus precios"
            if not existe and id_des is None:
                accion = "MOVER a destino NUEVO con sus precios"
            print("    ref dim_ori diseno_id={}: {}".format(r["diseno_id"], accion))

    if not ejecutar:
        print("\n[DRY-RUN] No se escribio nada. Usa --ejecutar para aplicar.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_unif_dim_{ts}.db")
    shutil.copy2(DB_PATH, backup)
    print(f"\n[BACKUP] {backup}")

    con.execute("BEGIN")
    for p in plan:
        id_des = p["id_des"]
        if p["crear_des"]:
            a_des = p["a_des"]
            r_des = p["r_des"]
            cur = con.execute(
                "INSERT INTO dimensiones_llanta (ancho, perfil, rin, sufijo) VALUES (?, NULL, ?, '')",
                (float(a_des), float(r_des)),
            )
            id_des = cur.lastrowid
            print("  [CREADA] dimensión {}R{} id={}".format(a_des, r_des, id_des))

        # Mover llantas
        con.execute("UPDATE llantas SET dimension_id=? WHERE dimension_id=?", (id_des, p["id_ori"]))
        # Catálogo: mover refs sin equivalente, eliminar las que duplican
        for ref_id in p["refs"]:
            diseno_id = con.execute("SELECT diseno_id FROM precios_producto WHERE id=?", (ref_id,)).fetchone()[0]
            existe = con.execute(
                "SELECT 1 FROM precios_producto WHERE dimension_id=? AND diseno_id=? AND id != ?",
                (id_des, diseno_id, ref_id),
            ).fetchone() is not None
            if existe:
                con.execute("DELETE FROM precios_producto WHERE id=?", (ref_id,))
                print("  [CATÁLOGO] eliminada ref de {} (destino conserva su precio)".format(p["nombre"]))
            else:
                con.execute("UPDATE precios_producto SET dimension_id=? WHERE id=?", (id_des, ref_id))
                print("  [CATÁLOGO] movida ref de {} a destino con sus precios".format(p["nombre"]))

        # Eliminar dimensión vieja (verificar 0 referencias)
        n_ll = con.execute("SELECT COUNT(*) FROM llantas WHERE dimension_id=?", (p["id_ori"],)).fetchone()[0]
        n_cat = con.execute("SELECT COUNT(*) FROM precios_producto WHERE dimension_id=?", (p["id_ori"],)).fetchone()[0]
        if n_ll == 0 and n_cat == 0:
            con.execute("DELETE FROM dimensiones_llanta WHERE id=?", (p["id_ori"],))
            print("  [DIMENSIÓN] {} eliminada".format(p["nombre"].split(" -> ")[0]))
        else:
            print("  [AVISO] dimensión {} NO eliminada (refs restantes: {} llantas, {} catálogo)".format(
                p["id_ori"], n_ll, n_cat))

    con.commit()
    print("\n[OK] Unificación aplicada.")


if __name__ == "__main__":
    main()