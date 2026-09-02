"""
Migración v2.8.1 — Índices para acelerar las queries de reportes y dashboard.

Índices creados (una sola vez):
    ix_llantas_estado           ON llantas(estado)
    ix_llantas_ubicacion_actual ON llantas(ubicacion_actual)
    ix_facturas_fecha_emision   ON facturas(fecha_emision)

Motivo: las queries de reportes/dashboard filtran por estado, ubicación y
fecha sobre ~24,451 llantas y las facturas. Sin índices, SQLite recorre las
tablas completas (full scan) en cada consulta → carga lenta del módulo
Reportes. Los índices NO modifican datos (estructura auxiliar de aceleración).

Uso (script CLI):
    python scripts/migrate_v2_8_1_indices.py --dry-run
    python scripts/migrate_v2_8_1_indices.py --apply

Mecanismo run_migration_once (main.py): la función run_migration() es
idempotente — verifica los índices y los crea solo si faltan.
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

INDICES = [
    ("ix_llantas_estado", "llantas", "estado"),
    ("ix_llantas_ubicacion_actual", "llantas", "ubicacion_actual"),
    ("ix_facturas_fecha_emision", "facturas", "fecha_emision"),
]


def indices_faltantes(cur: sqlite3.Cursor) -> list[str]:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'"
    )
    existentes = {r[0] for r in cur.fetchall()}
    return [nombre for nombre, _, _ in INDICES if nombre not in existentes]


def aplicar_migracion(cur: sqlite3.Cursor) -> list[str]:
    faltantes = indices_faltantes(cur)
    for nombre, tabla, columna in INDICES:
        if nombre in faltantes:
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {nombre} ON {tabla}({columna})"
            )
            print(f"  [OK]   Índice creado: {nombre} ON {tabla}({columna})")
        else:
            print(f"  [INFO] Índice ya existente: {nombre}")
    return faltantes


def verificar(cur: sqlite3.Cursor) -> bool:
    faltantes = indices_faltantes(cur)
    ok = not faltantes
    for nombre, tabla, columna in INDICES:
        estado = "OK" if nombre not in faltantes else "FALTA"
        print(f"  [{estado}] {nombre} ON {tabla}({columna})")
    return ok


def run(dry_run: bool) -> int:
    if not DB_PATH.exists():
        print(f"[ERROR]  No existe la BD en {DB_PATH}")
        return 1

    if dry_run:
        tmp = PROJECT_ROOT / "delca_indices_prueba.db"
        shutil.copy2(DB_PATH, tmp)
        print(f"[INFO]  MODO DRY-RUN — probando sobre copia temporal: {tmp.name}")
        conn = sqlite3.connect(tmp)
        try:
            cur = conn.cursor()
            faltantes = aplicar_migracion(cur)
            conn.commit()
            ok = verificar(cur)
            print(
                "\n[OK]  Dry-run exitoso — los índices se crearán sin tocar datos."
                if ok
                else "[ERROR]  Dry-run detectó problemas."
            )
            return 0 if ok else 1
        finally:
            conn.close()
            tmp.unlink(missing_ok=True)

    # Backup (precaución estándar del proyecto; los índices no modifican datos)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"delca_pre_v2_8_1_{fecha}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"[BACKUP]  Backup creado: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        aplicar_migracion(cur)
        conn.commit()
        ok = verificar(cur)
        if ok:
            print("\n[OK]  Migración v2.8.1 aplicada correctamente.")
            return 0
        print("\n[ERROR]  Migración completada pero faltan índices — revisa.")
        return 1
    except Exception as e:
        conn.rollback()
        print(f"[ERROR]  Error durante la migración: {e} — BD restaurada del backup")
        shutil.copy2(backup_path, DB_PATH)
        return 1
    finally:
        conn.close()


def run_migration() -> bool:
    """Función idempotente para el mecanismo run_migration_once de main.py."""
    if not DB_PATH.exists():
        print("[migracion] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        faltantes = indices_faltantes(cur)
        if not faltantes:
            print("[OK] Índices v2.8.1 ya aplicados — saltando.")
            return True

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"delca_pre_v2_8_1_{fecha}.db"
        shutil.copy2(DB_PATH, backup_path)
        print(f"[BACKUP]  Backup creado: {backup_path}")

        aplicar_migracion(cur)
        conn.commit()
        ok = verificar(cur)
        if not ok:
            conn.rollback()
            print("[ERROR]  Verificación falló — migración v2.8.1 no aplicada")
            return False
        print("[OK]  Migración v2.8.1 aplicada correctamente (run_migration)")
        return True
    except Exception as e:
        conn.rollback()
        print(f"[ERROR]  Migración v2.8.1 falló: {e}")
        return False
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migración v2.8.1 — índices para acelerar reportes"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Simular la migración sobre una copia temporal")
    parser.add_argument("--apply", action="store_true",
                        help="Aplicar la migración con backup previo")
    args = parser.parse_args()

    if args.dry_run:
        sys.exit(run(dry_run=True))
    if args.apply:
        sys.exit(run(dry_run=False))
    parser.print_help()


if __name__ == "__main__":
    main()