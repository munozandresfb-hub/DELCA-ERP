"""
Migration v2.2.0 — Diseños de banda independientes de la marca + campo tipo.

Cambia el catálogo de diseños:
- Se elimina la columna marca_id (los diseños ya no pertenecen a una marca).
- Se agrega la columna tipo: MIXTO / TRACCION / DIRECCIONAL.

Esquema nuevo de disenos_llanta:
    id      INTEGER PRIMARY KEY
    nombre  VARCHAR(100) NOT NULL  UNIQUE
    tipo    VARCHAR(20)  NOT NULL  DEFAULT 'MIXTO'
            CHECK (tipo IN ('MIXTO','TRACCION','DIRECCIONAL'))

Nota: la tabla actual está VACÍA (0 filas) y ninguna llanta usa diseno_id,
por lo que el rebuild no pierde datos. Las FKs de inventario que apuntan a
disenos_llanta (diseno_id) quedan intactas porque la tabla conserva su nombre.

Uso:
    python scripts/migrate_v2_2_0_diseno_independiente_tipo.py --dry-run
    python scripts/migrate_v2_2_0_diseno_independiente_tipo.py --apply

--dry-run: ejecuta el rebuild sobre una COPIA temporal de la BD y verifica.
--apply:   hace backup de la BD real en backups/ y aplica la migración.
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Consola Windows: forzar UTF-8 para caracteres acentuados
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "delca.db"
BACKUP_DIR = PROJECT_ROOT / "backups"

# ── Schema nuevo ─────────────────────────────────────────────────────────

CREATE_DISENOS_NUEVO = """
CREATE TABLE disenos_llanta_nuevo (
    id INTEGER NOT NULL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL DEFAULT 'MIXTO',
    CONSTRAINT uq_diseno_nombre UNIQUE (nombre),
    CONSTRAINT ck_diseno_tipo CHECK (tipo IN ('MIXTO', 'TRACCION', 'DIRECCIONAL'))
)
"""


# ── Helpers ─────────────────────────────────────────────────────────────

def contar_disenos(cur: sqlite3.Cursor) -> int:
    cur.execute("SELECT COUNT(*) FROM disenos_llanta")
    return cur.fetchone()[0]


def aplicar_migracion(cur: sqlite3.Cursor) -> None:
    """Recrea disenos_llanta sin marca_id y con columna tipo."""
    cur.execute("PRAGMA foreign_keys=OFF")

    # Crear tabla nueva (mismo id/nombre; tipo por defecto MIXTO)
    cur.execute(CREATE_DISENOS_NUEVO)
    cur.execute(
        "INSERT INTO disenos_llanta_nuevo (id, nombre) "
        "SELECT id, nombre FROM disenos_llanta"
    )
    cur.execute("DROP TABLE disenos_llanta")
    cur.execute("ALTER TABLE disenos_llanta_nuevo RENAME TO disenos_llanta")

    cur.execute("PRAGMA foreign_keys=ON")


def verificar(cur: sqlite3.Cursor) -> bool:
    ok = True

    cur.execute("PRAGMA integrity_check")
    if cur.fetchone()[0] != "ok":
        print("  [WARN]   integrity_check falló")
        ok = False

    cur.execute("PRAGMA foreign_key_check")
    violaciones = cur.fetchall()
    relevantes = [v for v in violaciones if "disenos_llanta" in (v[0], v[2])]
    if relevantes:
        print(f"  [WARN]   {len(relevantes)} violación(es) de FK sobre disenos_llanta: {relevantes[:5]}")
        ok = False
    elif violaciones:
        print(f"  [INFO]   {len(violaciones)} violación(es) de FK preexistentes ajenas (roles_permisos — ignoradas)")
    else:
        print("  [OK]  Sin violaciones de FK")

    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='disenos_llanta'"
    )
    sql = cur.fetchone()[0]
    print(f"  [INFO]   Esquema final:\n{sql}")
    if "marca_id" in sql:
        print("  [WARN]   marca_id aún presente")
        ok = False
    if "tipo" not in sql:
        print("  [WARN]   columna tipo ausente")
        ok = False

    if ok:
        print("  [OK]  Verificación completa: disenos_llanta independiente, con tipo")
    return ok


def run(dry_run: bool) -> int:
    if not DB_PATH.exists():
        print(f"[ERROR]  No existe la BD en {DB_PATH}")
        return 1

    if dry_run:
        tmp = PROJECT_ROOT / "delca_migracion_prueba.db"
        shutil.copy2(DB_PATH, tmp)
        print(f"[INFO]  MODO DRY-RUN — probando sobre copia temporal: {tmp.name}")
        conn = sqlite3.connect(tmp)
        try:
            cur = conn.cursor()
            print(f"\n[ANTES]  disenos_llanta: {contar_disenos(cur)} filas")
            aplicar_migracion(cur)
            conn.commit()
            print(f"[DESPUÉS] disenos_llanta: {contar_disenos(cur)} filas")
            ok = verificar(cur)
            print("\n" + ("[OK]  Dry-run exitoso — la migración es segura. Ejecuta --apply." if ok else "[ERROR]  Dry-run detectó problemas."))
            return 0 if ok else 1
        finally:
            conn.close()
            tmp.unlink(missing_ok=True)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"delca_pre_v2_2_0_{fecha}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"[BACKUP]  Backup creado: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        print(f"\n[ANTES]  disenos_llanta: {contar_disenos(cur)} filas")
        aplicar_migracion(cur)
        conn.commit()
        print(f"[DESPUÉS] disenos_llanta: {contar_disenos(cur)} filas")
        ok = verificar(cur)
        if ok:
            print("\n[OK]  Migración v2.2.0 aplicada correctamente.")
        else:
            print("\n[ERROR]  Migración completada pero con advertencias — revisa arriba.")
            return 1
        return 0
    except Exception as e:
        conn.rollback()
        print(f"[ERROR]  Error durante la migración: {e} — BD restaurada del backup")
        shutil.copy2(backup_path, DB_PATH)
        return 1
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migración v2.2.0 — diseños independientes de la marca con campo tipo"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular la migración sobre una copia temporal (sin tocar la BD real)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar la migración con backup previo",
    )
    args = parser.parse_args()

    if args.dry_run:
        sys.exit(run(dry_run=True))
    if args.apply:
        sys.exit(run(dry_run=False))
    parser.print_help()


if __name__ == "__main__":
    main()
