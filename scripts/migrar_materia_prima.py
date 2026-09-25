# -*- coding: utf-8 -*-
"""Migra el inventario de Materia Prima (bandas de reencauche) desde Excel.

Fuente: 'C:\\Users\\andre\\OneDrive\\Escritorio\\DELCA INVENTARIO. MIGRAR.xlsx'
Hoja: 'Materia prima ' (con espacio final)

Columnas: Nombre, Codigo, Precio Unitario, Cantidad en KG, Cantidad Rollos,
          Cantidad minima en planta, Unidad de medida, Fecha de ingreso

Mapeo:
  Nombre                -> productos.nombre
  Codigo                -> productos.sku (si falta, se genera del nombre)
  Precio Unitario       -> productos.costo_unitario (costo de la banda)
  Cantidad en KG        -> productos.stock_kg
  Cantidad Rollos       -> productos.stock
  Cantidad minima       -> productos.stock_minimo
  Unidad de medida      -> productos.unidad_medida ('ROLLO')
  Fecha de ingreso      -> movimiento ENTRADA (kardex) con esa fecha

Comportamiento: UPSERT por sku (existe -> actualiza; no existe -> crea).
Se excluyen filas sin datos reales (ej. 'Banda PBA' vacía).
Solo genera movimiento ENTRADA cuando Cantidad Rollos > 0.

Uso: python scripts/migrar_materia_prima.py [--dry-run | --ejecutar]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sqlite3
import unicodedata
from datetime import datetime

import openpyxl
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "delca.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
EXCEL_PATH = os.environ.get("DELCA_ARCHIVO_MATERIA_PRIMA", r"C:\Users\andre\OneDrive\Escritorio\DELCA INVENTARIO. MIGRAR.xlsx")
HOJA = "Materia prima "


def normalizar_sku(nombre: str) -> str:
    """Genera un SKU legible desde el nombre del producto (sin espacios/acentos)."""
    s = unicodedata.normalize("NFD", nombre)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^0-9A-Za-z]", "", s.upper())
    return s[:50]


def leer_excel() -> list[dict]:
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb[HOJA]
    filas = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        nombre = str(row[0]).strip() if row[0] is not None else ""
        codigo = str(row[1]).strip() if row[1] is not None else ""
        precio = row[2]
        kg = row[3]
        rollos = row[4]
        minimo = row[5]
        unidad = str(row[6]).strip() if row[6] is not None else "ROLLO"
        fecha = row[7]

        # fila sin nombre -> ignorar
        if not nombre:
            continue
        # fila sin datos reales (solo nombre) -> excluir (ej. 'Banda PBA')
        tiene_datos = any(v is not None and str(v).strip() != "" for v in (codigo, precio, kg, rollos, minimo))
        if not tiene_datos:
            continue

        def num(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        filas.append({
            "fila": i, "nombre": nombre, "codigo": codigo,
            "precio": num(precio), "kg": num(kg), "rollos": num(rollos),
            "minimo": num(minimo), "unidad": unidad or "ROLLO",
            "fecha": fecha,
        })
    return filas


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrar materia prima (bandas) desde Excel")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--dry-run", action="store_true", help="Solo simula (por defecto)")
    grupo.add_argument("--ejecutar", action="store_true", help="Aplica con backup")
    args = parser.parse_args()
    ejecutar = args.ejecutar

    if not os.path.exists(EXCEL_PATH):
        print(f"[ERROR] No se encuentra el Excel: {EXCEL_PATH}")
        return

    filas = leer_excel()
    print(f"[EXCEL] filas con datos: {len(filas)}")

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    plan = []
    sin_sku = 0
    for f in filas:
        sku = f["codigo"] or normalizar_sku(f["nombre"])
        if not f["codigo"]:
            sin_sku += 1
        existente = con.execute("SELECT id, nombre FROM productos WHERE sku = ?", (sku,)).fetchone()
        plan.append({
            "sku": sku, "existe": bool(existente),
            "nombre": f["nombre"], "precio": f["precio"], "kg": f["kg"],
            "rollos": f["rollos"], "minimo": f["minimo"], "unidad": f["unidad"],
            "fecha": f["fecha"], "fila": f["fila"],
        })

    n_crear = sum(1 for p in plan if not p["existe"])
    n_act = sum(1 for p in plan if p["existe"])
    n_mov = sum(1 for p in plan if p["rollos"] > 0)
    print(f"[PLAN] crear: {n_crear} | actualizar: {n_act} | movimientos ENTRADA: {n_mov} | sin SKU (generado): {sin_sku}")

    print("\n=== Muestra (primeras 8) ===")
    for p in plan[:8]:
        accion = "ACTUALIZAR" if p["existe"] else "CREAR"
        fecha_str = p["fecha"].strftime("%Y-%m-%d") if p["fecha"] else "?"
        print("  [{}] {} | sku={} | costo={:,.0f} | kg={} | rollos={} | min={} | und={} | fecha={}".format(
            accion, p["nombre"], p["sku"], p["precio"], p["kg"], p["rollos"], p["minimo"], p["unidad"], fecha_str))

    if not ejecutar:
        print("\n[DRY-RUN] No se escribio nada. Usa --ejecutar para aplicar.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"delca_pre_migrar_mp_{ts}.db")
    shutil.copy2(DB_PATH, backup)
    print(f"\n[BACKUP] {backup}")

    con.execute("BEGIN")
    for p in plan:
        if p["existe"]:
            con.execute(
                "UPDATE productos SET nombre=?, costo_unitario=?, stock=?, stock_kg=?, "
                "stock_minimo=?, unidad_medida=?, categoria='MATERIA_PRIMA' WHERE sku=?",
                (p["nombre"], p["precio"], p["rollos"], p["kg"], p["minimo"], p["unidad"], p["sku"]),
            )
        else:
            cur = con.execute(
                "INSERT INTO productos (nombre, sku, descripcion, categoria, stock, stock_kg, "
                "stock_minimo, costo_unitario, precio_venta, unidad_medida, activo) "
                "VALUES (?, ?, NULL, 'MATERIA_PRIMA', ?, ?, ?, ?, 0, ?, 1)",
                (p["nombre"], p["sku"], p["rollos"], p["kg"], p["minimo"], p["precio"], p["unidad"]),
            )
            p["producto_id"] = cur.lastrowid
        # Movimiento ENTRADA (kardex) solo si hay stock y es creación
        if p["rollos"] > 0:
            pid = p.get("producto_id")
            if pid is None:
                pid = con.execute("SELECT id FROM productos WHERE sku=?", (p["sku"],)).fetchone()[0]
            fecha = p["fecha"] if p["fecha"] else datetime.now()
            con.execute(
                "INSERT INTO movimientos_inventario (producto_id, tipo, cantidad, costo_unitario, "
                "referencia, observaciones, fecha) VALUES (?, 'ENTRADA', ?, ?, 'INVENTARIO_INICIAL', "
                "'Migración MP bandas', ?)",
                (pid, p["rollos"], p["precio"], fecha),
            )
    con.commit()
    print(f"[OK] Migración aplicada: {len(plan)} bandas.")


if __name__ == "__main__":
    main()