# -*- coding: utf-8 -*-
"""Limpia las facturas legacy de prueba y sus dependencias.

Elimina las 13 facturas de prueba (FAC-0001 a FAC-0013) creadas durante el
desarrollo, junto con sus pagos y vínculos a llantas. Estas facturas
inflaban la cartera pendiente ($4,166,000) y el gráfico de facturación
mensual, cuando en realidad no hay facturación real con las llantas migradas.

Orden de borrado (respetando FKs):
    1. pagos (factura_id)
    2. factura_llantas (factura_id)
    3. facturas

Modos:
    python scripts/limpiar_facturas_prueba.py             # DRY-RUN
    python scripts/limpiar_facturas_prueba.py --ejecutar  # REAL: backup + borra
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "delca.db"
BACKUP_DIR = PROJECT_ROOT / "backups"


def contar(cur: sqlite3.Cursor) -> dict:
    return {
        "facturas": cur.execute("SELECT COUNT(*) FROM facturas").fetchone()[0],
        "pagos": cur.execute("SELECT COUNT(*) FROM pagos").fetchone()[0],
        "factura_llantas": cur.execute("SELECT COUNT(*) FROM factura_llantas").fetchone()[0],
        "kpi_historico": cur.execute("SELECT COUNT(*) FROM kpi_historico").fetchone()[0],
    }


def aplicar(cur: sqlite3.Cursor) -> None:
    """Elimina las facturas legacy (todas, son de prueba) y sus rastros."""
    cur.execute("PRAGMA foreign_keys=OFF")
    cur.execute("DELETE FROM pagos")
    cur.execute("DELETE FROM factura_llantas")
    cur.execute("DELETE FROM facturas")
    # KPI histórico: los registros guardaban facturación de las facturas
    # legacy de prueba. El sistema regenera el mes actual al abrir el
    # dashboard (generar_registro_mes). Se eliminan los legacy.
    cur.execute("DELETE FROM kpi_historico")
    cur.execute("PRAGMA foreign_keys=ON")


def verificar(cur: sqlite3.Cursor) -> bool:
    ok = True
    n = contar(cur)
    if n["facturas"] or n["pagos"] or n["factura_llantas"] or n["kpi_historico"]:
        print(f"  [WARN] Quedan registros: {n}")
        ok = False
    cur.execute("PRAGMA integrity_check")
    if cur.fetchone()[0] != "ok":
        print("  [WARN] integrity_check falló")
        ok = False
    print(f"  [OK] {'Facturas/pagos/KPI limpios, ' if ok else ''}BD íntegra")
    return ok


def run(dry_run: bool) -> int:
    if not DB_PATH.exists():
        print(f"[ERROR] No existe la BD en {DB_PATH}")
        return 1

    if dry_run:
        tmp = PROJECT_ROOT / "delca_migracion_prueba.db"
        shutil.copy2(DB_PATH, tmp)
        print(f"[INFO]  MODO DRY-RUN — copia temporal: {tmp.name}")
        conn = sqlite3.connect(tmp)
        try:
            cur = conn.cursor()
            antes = contar(cur)
            print(f"[ANTES] {antes}")
            aplicar(cur)
            conn.commit()
            verificar(cur)
            print("[OK] Dry-run exitoso — la limpieza es segura. Ejecuta --ejecutar.")
            return 0
        finally:
            conn.close()
            tmp.unlink(missing_ok=True)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"delca_pre_limpieza_facturas_{fecha}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"[BACKUP] {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        antes = contar(cur)
        print(f"[ANTES] {antes}")
        aplicar(cur)
        conn.commit()
        ok = verificar(cur)
        print("\n[OK] Limpieza aplicada." if ok else "\n[ERROR] Con advertencias.")
        return 0 if ok else 1
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e} — BD restaurada del backup")
        shutil.copy2(backup_path, DB_PATH)
        return 1
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Limpiar facturas legacy de prueba")
    parser.add_argument("--ejecutar", action="store_true",
                        help="Aplica la limpieza con backup (por defecto solo simula)")
    args = parser.parse_args()
    if args.ejecutar:
        sys.exit(run(dry_run=False))
    sys.exit(run(dry_run=True))


if __name__ == "__main__":
    main()