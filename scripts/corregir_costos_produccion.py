"""
Migración/corrección v2.8.11 — Alinear costo_produccion de las llantas al
catálogo de precios (precios_producto.costo_fabricacion) por diseño+dimensión.

Problema: 7,906 llantas sin costo_produccion (el reporte de Llantas muestra
"costo" vacío) y 16,399 con costo histórico que no coincide con el catálogo
de precios (fuente de verdad según el usuario: el costo está en
Facturación-Precios).

Solución: actualizar llantas.costo_produccion = precios_producto.costo_fabricacion
para TODAS las llantas con diseño+dimensión que tengan precio en el catálogo.
Las llantas sin precio (combinación no cubierta) quedan sin costo (se reportan).

Seguridades:
    --dry-run: simula y reporta el impacto sin escribir.
    --ejecutar: crea backup y aplica.
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

SQL_ACTUALIZAR = """
UPDATE llantas
SET costo_produccion = (
    SELECT p.costo_fabricacion
    FROM precios_producto p
    WHERE p.diseno_id = llantas.diseno_id
      AND p.dimension_id = llantas.dimension_id
      AND p.costo_fabricacion IS NOT NULL
      AND p.costo_fabricacion > 0
)
WHERE (llantas.costo_produccion IS NULL OR llantas.costo_produccion != (
    SELECT p.costo_fabricacion
    FROM precios_producto p
    WHERE p.diseno_id = llantas.diseno_id
      AND p.dimension_id = llantas.dimension_id
      AND p.costo_fabricacion IS NOT NULL
      AND p.costo_fabricacion > 0
))
"""


def impacto(cur: sqlite3.Cursor) -> dict:
    total = cur.execute("SELECT COUNT(*) FROM llantas").fetchone()[0]
    con_costo = cur.execute(
        "SELECT COUNT(*) FROM llantas WHERE costo_produccion > 0"
    ).fetchone()[0]
    sin_costo = cur.execute(
        "SELECT COUNT(*) FROM llantas WHERE costo_produccion IS NULL OR costo_produccion = 0"
    ).fetchone()[0]
    # cuántas tienen precio en el catálogo (podrían tener costo)
    con_precio = cur.execute(
        """
        SELECT COUNT(*) FROM llantas l
        WHERE EXISTS (
            SELECT 1 FROM precios_producto p
            WHERE p.diseno_id = l.diseno_id AND p.dimension_id = l.dimension_id
              AND p.costo_fabricacion > 0
        )
        """
    ).fetchone()[0]
    # cuántas cambiarían (costo actual != costo catálogo)
    cambiarian = cur.execute(
        """
        SELECT COUNT(*) FROM llantas l
        WHERE EXISTS (
            SELECT 1 FROM precios_producto p
            WHERE p.diseno_id = l.diseno_id AND p.dimension_id = l.dimension_id
              AND p.costo_fabricacion > 0
        )
        AND (l.costo_produccion IS NULL OR l.costo_produccion != (
            SELECT p.costo_fabricacion FROM precios_producto p
            WHERE p.diseno_id = l.diseno_id AND p.dimension_id = l.dimension_id
              AND p.costo_fabricacion > 0
        ))
        """
    ).fetchone()[0]
    return {
        "total": total, "con_costo": con_costo, "sin_costo": sin_costo,
        "con_precio": con_precio, "cambiarian": cambiarian,
    }


def run(dry_run: bool) -> int:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        antes = impacto(cur)
        print(f"[ANTES]   total={antes['total']} | con_costo={antes['con_costo']} "
              f"| sin_costo={antes['sin_costo']}")
        print(f"[INFO]    llantas con precio en catálogo (podrían tener costo): {antes['con_precio']}")
        print(f"[INFO]    llantas que CAMBIARÍAN al costo del catálogo: {antes['cambiarian']}")

        if dry_run:
            print("\n[DRY-RUN] No se escribió nada. Ejecuta --ejecutar para aplicar.")
            conn.close()
            return 0

        # Backup
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"delca_pre_costos_{fecha}.db"
        shutil.copy2(DB_PATH, backup_path)
        print(f"[BACKUP]  {backup_path}")

        cur.execute(SQL_ACTUALIZAR)
        conn.commit()

        despues = impacto(cur)
        print(f"[DESPUÉS] total={despues['total']} | con_costo={despues['con_costo']} "
              f"| sin_costo={despues['sin_costo']}")
        print(f"[OK]      Costos alineados al catálogo (cambiaron {antes['cambiarian']} llantas).")
        return 0
    except Exception as e:
        conn.rollback()
        print(f"[ERROR]   {e}")
        return 1
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Alinear costos de producción al catálogo")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin escribir")
    parser.add_argument("--ejecutar", action="store_true", help="Aplicar con backup")
    args = parser.parse_args()
    if args.dry_run:
        sys.exit(run(dry_run=True))
    if args.ejecutar:
        sys.exit(run(dry_run=False))
    parser.print_help()


if __name__ == "__main__":
    main()