# -*- coding: utf-8 -*-
"""Unifica dimensiones con sufijo (U, C) a su base sin sufijo (mismo ancho/perfil/rin).

Ej: 295/80R22.5U -> 295/80R22.5 · 215/75R16C -> 215/75R16 · 7.5R16U -> 7.5R16

Conserva TODAS las características de la llanta (diseño, estado, ubicación,
DOT, orden, cliente, tiquete); solo cambia dimension_id (y el texto dimension).

Precios (precios_producto): los de la base se conservan; los del sufijo sin
equivalente (por diseño) se mueven a la base; los duplicados se eliminan.
La dimensión con sufijo se elimina al final (queda sin referencias).

Uso: python scripts/unificar_dimensiones_sufijo.py
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(PROJECT_ROOT, "delca.db")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups", "migracion")


def display(ancho, perfil, rin) -> str:
    """Representación estándar de la dimensión: 7.5R16, 215/75R16, 295/80R22.5."""
    a = f"{ancho:g}"
    p = f"/{perfil}" if perfil is not None else ""
    return f"{a}{p}R{rin:g}"


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_unificar_sufijos_{ts}.db")
    shutil.copy2(DB, backup)
    print(f"[BACKUP] {backup}")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # ── Pares: (dimensión con sufijo -> base sin sufijo) con mismo ancho/perfil/rin ──
    pares = []
    sufijos = cur.execute(
        "SELECT id, ancho, perfil, rin, sufijo FROM dimensiones_llanta "
        "WHERE sufijo IS NOT NULL AND sufijo != ''"
    ).fetchall()
    for s in sufijos:
        if s["perfil"] is None:
            base = cur.execute(
                "SELECT id FROM dimensiones_llanta WHERE ancho=? AND perfil IS NULL "
                "AND rin=? AND (sufijo IS NULL OR sufijo='')",
                (s["ancho"], s["rin"]),
            ).fetchone()
        else:
            base = cur.execute(
                "SELECT id FROM dimensiones_llanta WHERE ancho=? AND perfil=? "
                "AND rin=? AND (sufijo IS NULL OR sufijo='')",
                (s["ancho"], s["perfil"], s["rin"]),
            ).fetchone()
        if base:
            pares.append((s, base["id"]))
        else:
            print(f"[SIN BASE] id={s['id']} ({display(s['ancho'], s['perfil'], s['rin'])}{s['sufijo']}) - se omite")

    total_llantas = 0
    for s, base_id in pares:
        suf_id = s["id"]
        n_ll = cur.execute(
            "SELECT COUNT(*) FROM llantas WHERE dimension_id=?", (suf_id,)
        ).fetchone()[0]

        # Precios: conservar los de la base; mover los del sufijo sin equivalente; eliminar duplicados
        precios_sufijo = cur.execute(
            "SELECT id, diseno_id FROM precios_producto WHERE dimension_id=?", (suf_id,)
        ).fetchall()
        movidos, eliminados = 0, 0
        for p in precios_sufijo:
            tiene_base = cur.execute(
                "SELECT 1 FROM precios_producto WHERE dimension_id=? AND diseno_id=?",
                (base_id, p["diseno_id"]),
            ).fetchone()
            if tiene_base:
                cur.execute("DELETE FROM precios_producto WHERE id=?", (p["id"],))
                eliminados += 1
            else:
                cur.execute(
                    "UPDATE precios_producto SET dimension_id=? WHERE id=?",
                    (base_id, p["id"]),
                )
                movidos += 1

        # Llantas: solo cambia dimension_id (y el texto dimension)
        texto_base = display(s["ancho"], s["perfil"], s["rin"])
        cur.execute(
            "UPDATE llantas SET dimension_id=?, dimension=? WHERE dimension_id=?",
            (base_id, texto_base, suf_id),
        )

        # Eliminar la dimensión con sufijo
        cur.execute("DELETE FROM dimensiones_llanta WHERE id=?", (suf_id,))

        total_llantas += n_ll
        print(
            f"[OK] {display(s['ancho'], s['perfil'], s['rin'])}{s['sufijo']} -> "
            f"{texto_base} | llantas: {n_ll} | precios movidos: {movidos} | eliminados: {eliminados}"
        )

    con.commit()
    print(f"\n=== REPORTE ===")
    print(f"  Dimensiones unificadas: {len(pares)}")
    print(f"  Llantas reasignadas: {total_llantas}")
    print(f"  Backup: {backup}")
    con.close()
    print("UNIFICACION APLICADA OK")


if __name__ == "__main__":
    main()