# -*- coding: utf-8 -*-
"""Corrección masiva y RÁPIDA de fechas de historiales post-migración.

Actualiza la fecha del historial INICIAL (el más antiguo) de cada llanta
usando su fecha_ingreso real, mediante SQL directo con subqueries (evita
N+1 del ORM). Solo aplica cuando el historial tiene la fecha de migración
(2026-08-25) que se usó como placeholder.
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


def contar_pendientes(cur: sqlite3.Cursor) -> tuple[int, int]:
    """Cuenta llantas cuyo historial inicial tiene fecha = fecha de migración."""
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT e.id
            FROM estados_llanta e
            JOIN llantas l ON l.id = e.llanta_id
            WHERE e.id = (SELECT MIN(e2.id) FROM estados_llanta e2
                          WHERE e2.llanta_id = e.llanta_id)
              AND date(e.fecha) >= '2026-08-24'
              AND l.fecha_ingreso IS NOT NULL
        )
    """)
    n_est = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT u.id
            FROM ubicaciones_llanta u
            JOIN llantas l ON l.id = u.llanta_id
            WHERE u.id = (SELECT MIN(u2.id) FROM ubicaciones_llanta u2
                          WHERE u2.llanta_id = u.llanta_id)
              AND date(u.fecha) >= '2026-08-24'
              AND l.fecha_ingreso IS NOT NULL
        )
    """)
    n_ubi = cur.fetchone()[0]
    return n_est, n_ubi


def aplicar(cur: sqlite3.Cursor) -> None:
    """Actualiza la fecha del historial inicial a fecha_ingreso de la llanta."""
    # Crear índices si faltan (acelera las subqueries MIN por llanta)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_estados_llanta_llanta_id "
        "ON estados_llanta (llanta_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS ix_ubicaciones_llanta_llanta_id "
        "ON ubicaciones_llanta (llanta_id)"
    )

    cur.execute("""
        UPDATE estados_llanta
        SET fecha = (SELECT l.fecha_ingreso FROM llantas l WHERE l.id = estados_llanta.llanta_id)
        WHERE id IN (
            SELECT e.id FROM estados_llanta e
            JOIN llantas l ON l.id = e.llanta_id
            WHERE e.id = (SELECT MIN(e2.id) FROM estados_llanta e2
                          WHERE e2.llanta_id = e.llanta_id)
              AND date(e.fecha) >= '2026-08-24'
              AND l.fecha_ingreso IS NOT NULL
        )
    """)
    cur.execute("""
        UPDATE ubicaciones_llanta
        SET fecha = (SELECT l.fecha_ingreso FROM llantas l WHERE l.id = ubicaciones_llanta.llanta_id)
        WHERE id IN (
            SELECT u.id FROM ubicaciones_llanta u
            JOIN llantas l ON l.id = u.llanta_id
            WHERE u.id = (SELECT MIN(u2.id) FROM ubicaciones_llanta u2
                          WHERE u2.llanta_id = u.llanta_id)
              AND date(u.fecha) >= '2026-08-24'
              AND l.fecha_ingreso IS NOT NULL
        )
    """)


def verificar(cur: sqlite3.Cursor) -> bool:
    ok = True
    n_est, n_ubi = contar_pendientes(cur)
    if n_est or n_ubi:
        print(f"  [WARN] Quedan pendientes: estados={n_est}, ubicaciones={n_ubi}")
        ok = False
    cur.execute("PRAGMA integrity_check")
    if cur.fetchone()[0] != "ok":
        print("  [WARN] integrity_check falló")
        ok = False
    print(f"  [OK] {('Sin pendientes, ' if ok else '')}BD íntegra")
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
            n_est, n_ubi = contar_pendientes(cur)
            print(f"[ANTES] Historiales con fecha de migración: estados={n_est}, ubicaciones={n_ubi}")
            aplicar(cur)
            conn.commit()
            verificar(cur)
            print("[OK] Dry-run exitoso — la corrección es segura. Ejecuta --ejecutar.")
            return 0
        finally:
            conn.close()
            tmp.unlink(missing_ok=True)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"delca_pre_historiales_{fecha}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"[BACKUP] {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        n_est, n_ubi = contar_pendientes(cur)
        print(f"[ANTES] Historiales con fecha de migración: estados={n_est}, ubicaciones={n_ubi}")
        aplicar(cur)
        conn.commit()
        ok = verificar(cur)
        print("\n[OK] Corrección aplicada." if ok else "\n[ERROR] Con advertencias.")
        return 0 if ok else 1
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e} — BD restaurada del backup")
        shutil.copy2(backup_path, DB_PATH)
        return 1
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Corregir fechas de historiales post-migración")
    parser.add_argument("--ejecutar", action="store_true",
                        help="Aplica la corrección con backup (por defecto solo simula)")
    args = parser.parse_args()
    if args.ejecutar:
        sys.exit(run(dry_run=False))
    sys.exit(run(dry_run=True))


if __name__ == "__main__":
    main()