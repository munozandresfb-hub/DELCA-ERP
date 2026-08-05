"""
Migration v2.1.0 — Medida de llanta con perfil opcional.

Permite registrar medidas sin perfil (solo ancho + rin), p.ej. dimensiones
de camión/industriales que no usan relación de aspecto.

Cambio de esquema:
    medidas_llanta.perfil  INTEGER NOT NULL  →  INTEGER (nullable)

SQLite no soporta "ALTER COLUMN DROP NOT NULL": la tabla se RECREA con el
mismo esquema (perfil nullable), se copian los datos (ids preservados), se
elimina la tabla vieja y se renombra la nueva. Las FKs de otras tablas que
referencian medidas_llanta.id quedan intactas porque los ids no cambian.

Uso:
    python scripts/migrate_v2_1_0_medida_perfil_opcional.py --dry-run
    python scripts/migrate_v2_1_0_medida_perfil_opcional.py --apply

--dry-run: ejecuta el rebuild sobre una COPIA temporal de la BD y reporta
           conteos antes/después + verificación de integridad. No toca la BD real.
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

# ── Schema nuevo (perfil nullable) ───────────────────────────────────────

CREATE_MEDIDAS_NUEVO = """
CREATE TABLE medidas_llanta_nuevo (
    id INTEGER NOT NULL PRIMARY KEY,
    ancho INTEGER NOT NULL,
    perfil INTEGER,
    rin INTEGER NOT NULL,
    UNIQUE (ancho, perfil, rin)
)
"""


# ── Helpers ─────────────────────────────────────────────────────────────

def contar_medidas(cur: sqlite3.Cursor) -> tuple[int, int]:
    """Devuelve (total_filas, filas_con_perfil_null)."""
    cur.execute("SELECT COUNT(*) FROM medidas_llanta")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM medidas_llanta WHERE perfil IS NULL")
    nulos = cur.fetchone()[0]
    return total, nulos


def aplicar_migracion(cur: sqlite3.Cursor) -> None:
    """Recrea medidas_llanta con perfil nullable, preservando datos e ids."""
    # Desactivar FKs durante el rebuild (la tabla se renombra temporalmente)
    cur.execute("PRAGMA foreign_keys=OFF")

    cur.execute(CREATE_MEDIDAS_NUEVO)
    cur.execute(
        "INSERT INTO medidas_llanta_nuevo (id, ancho, perfil, rin) "
        "SELECT id, ancho, perfil, rin FROM medidas_llanta"
    )
    cur.execute("DROP TABLE medidas_llanta")
    cur.execute("ALTER TABLE medidas_llanta_nuevo RENAME TO medidas_llanta")

    cur.execute("PRAGMA foreign_keys=ON")


def verificar(cur: sqlite3.Cursor) -> bool:
    """Verifica integridad de la BD tras el rebuild."""
    ok = True

    cur.execute("PRAGMA integrity_check")
    if cur.fetchone()[0] != "ok":
        print("  [WARN]   integrity_check falló")
        ok = False

    cur.execute("PRAGMA foreign_key_check")
    violaciones = cur.fetchall()
    # Solo importan las violaciones que involucran a medidas_llanta (padre o hija).
    # roles_permisos → roles tiene violaciones PREEXISTENTES ajenas a esta migración.
    relevantes = [v for v in violaciones if "medidas_llanta" in (v[0], v[2])]
    if relevantes:
        print(f"  [WARN]   {len(relevantes)} violación(es) de FK sobre medidas_llanta: {relevantes[:5]}")
        ok = False
    elif violaciones:
        print(f"  [INFO]   {len(violaciones)} violación(es) de FK preexistentes ajenas a esta migración (ignoradas)")
    else:
        print("  [OK]  Sin violaciones de FK")

    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='medidas_llanta'"
    )
    sql = cur.fetchone()[0]
    print(f"  [INFO]   Esquema final:\n{sql}")
    if "perfil INTEGER NOT NULL" in sql:
        print("  [WARN]   perfil sigue siendo NOT NULL")
        ok = False

    if ok:
        print("  [OK]  Verificación completa: BD íntegra, perfil ahora nullable")
    return ok


def run(dry_run: bool) -> int:
    if not DB_PATH.exists():
        print(f"[ERROR]  No existe la BD en {DB_PATH}")
        return 1

    # ── Modo dry-run: trabajar sobre copia temporal ──
    if dry_run:
        tmp = PROJECT_ROOT / "delca_migracion_prueba.db"
        shutil.copy2(DB_PATH, tmp)
        print(f"[INFO]  MODO DRY-RUN — probando sobre copia temporal: {tmp.name}")
        conn = sqlite3.connect(tmp)
        try:
            cur = conn.cursor()

            antes_total, antes_nulos = contar_medidas(cur)
            print(f"\n[ANTES]  medidas_llanta: {antes_total} filas ({antes_nulos} con perfil NULL)")

            aplicar_migracion(cur)
            conn.commit()

            despues_total, despues_nulos = contar_medidas(cur)
            print(f"[DESPUÉS] medidas_llanta: {despues_total} filas ({despues_nulos} con perfil NULL)")

            # Comprobar que los ids se preservaron (muestra)
            cur.execute("SELECT MIN(id), MAX(id) FROM medidas_llanta")
            min_id, max_id = cur.fetchone()
            print(f"[INFO]   Rango de ids preservado: {min_id}–{max_id}")

            ok = verificar(cur)
            print("\n" + ("[OK]  Dry-run exitoso — la migración es segura. Ejecuta --apply." if ok else "[ERROR]  Dry-run detectó problemas."))
            return 0 if ok else 1
        finally:
            conn.close()
            tmp.unlink(missing_ok=True)

    # ── Modo apply: backup + migración real ──
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"delca_pre_v2_1_0_{fecha}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"[BACKUP]  Backup creado: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        antes_total, antes_nulos = contar_medidas(cur)
        print(f"\n[ANTES]  medidas_llanta: {antes_total} filas ({antes_nulos} con perfil NULL)")

        aplicar_migracion(cur)
        conn.commit()

        despues_total, despues_nulos = contar_medidas(cur)
        print(f"[DESPUÉS] medidas_llanta: {despues_total} filas ({despues_nulos} con perfil NULL)")

        ok = verificar(cur)
        if ok:
            print("\n[OK]  Migración v2.1.0 aplicada correctamente.")
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
        description="Migración v2.1.0 — medida de llanta con perfil opcional"
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
