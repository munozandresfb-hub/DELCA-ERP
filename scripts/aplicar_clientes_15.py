# -*- coding: utf-8 -*-
"""Asigna llantas sin cliente: DELCA (9) + PORTILLO WILBER (2, creado con NIT).

Pendiente: HERRERA ESTEBAN 2 (falta NIT del usuario) - 4 llantas (25042-45).
Uso: python scripts/aplicar_clientes_15.py [--dry-run | --ejecutar]
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

# clientes existentes (por nombre exacto)
EXISTENTES = {
    "DELCA": ["6659", "8251", "9588", "9589", "9590", "12491", "12492", "12516", "12517"],
}
# clientes a crear (nombre -> datos + tiquetes)
CREAR = {
    "PORTILLO WILBER": {
        "nit": "1085250619", "telefono": "3112563822", "celular": "",
        "tqs": ["25064", "25065"],
    },
    "HERRERA ESTEBAN 2": {
        "nit": "1085106383", "telefono": "3206669663", "celular": "",
        "tqs": ["25042", "25043", "25044", "25045"],
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Asignar llantas sin cliente (DELCA + PORTILLO WILBER)")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo simula (por defecto)")
    grupo.add_argument("--ejecutar", action="store_true", help="Aplica con backup")
    args = parser.parse_args()
    ejecutar = args.ejecutar

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    # Resolver/crear clientes (idempotente: si ya existe por NIT o nombre, se reutiliza)
    plan = []
    for nombre, tqs in EXISTENTES.items():
        c = con.execute("SELECT id, nombre FROM cliente WHERE UPPER(nombre) = ?", (nombre.upper(),)).fetchone()
        if not c:
            print("[ERROR] Cliente {!r} no existe. Abortando.".format(nombre))
            return
        plan.append({"nombre": nombre, "id": c["id"], "crear": False, "tqs": tqs, "extra": None})
    for nombre, info in CREAR.items():
        c = con.execute("SELECT id, nombre FROM cliente WHERE UPPER(nombre) = ?", (nombre.upper(),)).fetchone()
        if c:
            plan.append({"nombre": nombre, "id": c["id"], "crear": False, "tqs": info["tqs"], "extra": None})
            continue
        duplicado = con.execute("SELECT id, nombre FROM cliente WHERE nit = ?", (info["nit"],)).fetchone()
        if duplicado:
            print("[ERROR] NIT {} ya existe en id={} {!r}. Abortando.".format(info["nit"], duplicado["id"], duplicado["nombre"]))
            return
        plan.append({"nombre": nombre, "id": None, "crear": True, "tqs": info["tqs"], "extra": info})

    print("=== PLAN ===")
    for p in plan:
        print("  {!r} ({}): {} llantas".format(p["nombre"], "crear" if p["crear"] else "existe id={}".format(p["id"]), len(p["tqs"])))

    for p in plan:
        for tq in p["tqs"]:
            l = con.execute("SELECT tiquete, numero_orden, consecutivo, cliente_id FROM llantas WHERE tiquete=?", (tq,)).fetchone()
            if not l:
                print("  !! {} NO ENCONTRADA".format(tq))
                continue
            print("     {} (O.S.{}-{}) -> {!r}".format(tq, l["numero_orden"], l["consecutivo"], p["nombre"]))

    if not ejecutar:
        print("\n[DRY-RUN] No se escribio nada. Usa --ejecutar para aplicar.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_llantas_cliente_{ts}.db")
    shutil.copy2(DB_PATH, backup)
    print(f"\n[BACKUP] {backup}")

    con.execute("BEGIN")
    for p in plan:
        if p["crear"]:
            info = p["extra"]
            cur = con.execute(
                "INSERT INTO cliente (nombre, nit, telefono, celular, saldo, activo, categoria_abc) "
                "VALUES (?, ?, ?, ?, 0, 1, 'B')",
                (p["nombre"], info["nit"], info.get("telefono", ""), info.get("celular", "")),
            )
            p["id"] = cur.lastrowid
            print("  [CREADO] {!r} id={} NIT={}".format(p["nombre"], p["id"], info["nit"]))
        for tq in p["tqs"]:
            con.execute("UPDATE llantas SET cliente_id = ? WHERE tiquete = ?", (p["id"], tq))
    con.commit()
    print("[OK] Asignadas {} llantas.".format(sum(len(p["tqs"]) for p in plan)))


if __name__ == "__main__":
    main()