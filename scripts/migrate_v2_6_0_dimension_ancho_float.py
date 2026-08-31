"""
Migration v2.6.0 — Dimensión de llanta: ancho FLOAT + sufijo visible.

Cambio de esquema:
    dimensiones_llanta.ancho   INTEGER      → FLOAT   (permite 9.5, 7.50)
    dimensiones_llanta.sufijo  (nuevo)      VARCHAR(10) NOT NULL DEFAULT ''
    UNIQUE (ancho, perfil, rin)              → UNIQUE (ancho, perfil, rin, sufijo)

Motivo: el importador legacy produce dimensiones con ancho decimal
(9.5R17.5, 7.50R16) y sufijos visibles (215/75R16C, 295/80R22.5U) que el
modelo anterior no podía representar.

SQLite no soporta ALTER: la tabla se RECREA, se copian los datos (ids
preservados), se elimina la vieja y se renombra la nueva. Las FKs de
precios_producto.medida_id → dimensiones_llanta.id quedan intactas porque
los ids no cambian.

Uso:
    python scripts/migrate_v2_6_0_dimension_ancho_float.py --dry-run
    python scripts/migrate_v2_6_0_dimension_ancho_float.py --apply
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

CREATE_DIMENSIONES_NUEVO = """
CREATE TABLE dimensiones_llanta_nuevo (
    id INTEGER NOT NULL PRIMARY KEY,
    ancho FLOAT,
    perfil INTEGER,
    rin FLOAT,
    sufijo VARCHAR(10) NOT NULL DEFAULT '',
    UNIQUE (ancho, perfil, rin, sufijo)
)
"""

COLUMNAS = ["id", "ancho", "perfil", "rin", "sufijo"]


def contar(cur: sqlite3.Cursor) -> int:
    cur.execute("SELECT COUNT(*) FROM dimensiones_llanta")
    return cur.fetchone()[0]


def aplicar_migracion(cur: sqlite3.Cursor) -> None:
    cur.execute("PRAGMA foreign_keys=OFF")

    # Asegurar columna sufijo en la tabla vieja (puede no existir)
    cur.execute("PRAGMA table_info(dimensiones_llanta)")
    cols = {row[1] for row in cur.fetchall()}
    if "sufijo" not in cols:
        cur.execute(
            "ALTER TABLE dimensiones_llanta ADD COLUMN sufijo VARCHAR(10) NOT NULL DEFAULT ''"
        )

    cur.execute(CREATE_DIMENSIONES_NUEVO)
    cols = ", ".join(COLUMNAS)
    cur.execute(
        f"INSERT INTO dimensiones_llanta_nuevo ({cols}) "
        f"SELECT {cols} FROM dimensiones_llanta"
    )
    cur.execute("DROP TABLE dimensiones_llanta")
    cur.execute("ALTER TABLE dimensiones_llanta_nuevo RENAME TO dimensiones_llanta")
    cur.execute("PRAGMA foreign_keys=ON")


def verificar(cur: sqlite3.Cursor) -> bool:
    ok = True
    cur.execute("PRAGMA integrity_check")
    if cur.fetchone()[0] != "ok":
        print("  [WARN]   integrity_check falló")
        ok = False

    cur.execute("PRAGMA foreign_key_check")
    violaciones = cur.fetchall()
    relevantes = [v for v in violaciones if "dimensiones_llanta" in (v[0], v[2])]
    if relevantes:
        print(f"  [WARN]   {len(relevantes)} violación(es) de FK: {relevantes[:5]}")
        ok = False
    elif violaciones:
        print(f"  [INFO]   {len(violaciones)} violación(es) preexistentes ajenas (ignoradas)")
    else:
        print("  [OK]  Sin violaciones de FK")

    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='dimensiones_llanta'"
    )
    sql = cur.fetchone()[0]
    print(f"  [INFO]   Esquema final:\n{sql}")
    if "FLOAT" not in sql or "sufijo" not in sql:
        print("  [WARN]   ancho/sufijo no quedaron aplicados")
        ok = False

    # Insert de prueba con ancho decimal + sufijo
    cur.execute(
        "INSERT INTO dimensiones_llanta (id, ancho, perfil, rin, sufijo) "
        "VALUES (999999, 9.5, NULL, 17.5, 'C')"
    )
    cur.execute("DELETE FROM dimensiones_llanta WHERE id = 999999")
    print("  [OK]  Insert con ancho decimal + sufijo permitido")

    if ok:
        print("  [OK]  Verificación completa: esquema correcto, BD íntegra")
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
            antes = contar(cur)
            print(f"[ANTES]  dimensiones_llanta: {antes} filas")
            aplicar_migracion(cur)
            conn.commit()
            despues = contar(cur)
            print(f"[DESPUÉS] dimensiones_llanta: {despues} filas")
            cur.execute("SELECT MIN(id), MAX(id) FROM dimensiones_llanta")
            min_id, max_id = cur.fetchone()
            print(f"[INFO]   Rango de ids preservado: {min_id}–{max_id}")
            ok = verificar(cur)
            print("\n" + ("[OK]  Dry-run exitoso — la migración es segura. Ejecuta --apply."
                          if ok else "[ERROR]  Dry-run detectó problemas."))
            return 0 if ok else 1
        finally:
            conn.close()
            tmp.unlink(missing_ok=True)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"delca_pre_v2_6_0_{fecha}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"[BACKUP]  Backup creado: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        antes = contar(cur)
        print(f"[ANTES]  dimensiones_llanta: {antes} filas")
        aplicar_migracion(cur)
        conn.commit()
        despues = contar(cur)
        print(f"[DESPUÉS] dimensiones_llanta: {despues} filas")
        ok = verificar(cur)
        if ok:
            print("\n[OK]  Migración v2.6.0 aplicada correctamente.")
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


def run_migration() -> bool:
    """Función idempotente para el mecanismo run_migration_once de main.py."""
    if not DB_PATH.exists():
        print("[migracion] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='dimensiones_llanta'"
        )
        fila = cur.fetchone()
        if fila and fila[0] and "sufijo" in fila[0] and "FLOAT" in fila[0]:
            print("[OK] Dimensión v2.6.0 ya aplicada — saltando.")
            return True

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"delca_pre_v2_6_0_{fecha}.db"
        shutil.copy2(DB_PATH, backup_path)
        print(f"[BACKUP]  Backup creado: {backup_path}")

        aplicar_migracion(cur)
        conn.commit()
        ok = verificar(cur)
        if not ok:
            conn.rollback()
            print("[ERROR]  Verificación falló — migración v2.6.0 no aplicada")
            return False
        print("[OK]  Migración v2.6.0 aplicada correctamente (run_migration)")
        return True
    except Exception as e:
        conn.rollback()
        print(f"[ERROR]  Migración v2.6.0 falló: {e}")
        return False
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migración v2.6.0 — dimensión ancho FLOAT + sufijo"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Simular la migración sobre una copia temporal (sin tocar la BD real)")
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