"""
Migration v2.4.0 — Factura con llanta nueva (item manual sin registro en llantas).

Permite que una factura incluya llantas NUEVAS vendidas directamente, sin
registro previo en la tabla `llantas` (que es el inventario de reencauche).
La línea de factura guarda una descripción libre (``descripcion``) y el
``llanta_id`` pasa a ser opcional (NULL).

Cambio de esquema:
    factura_llantas.llanta_id  INTEGER NOT NULL  →  INTEGER (nullable)
    factura_llantas.descripcion  (nueva columna)  →  VARCHAR(200) NULL

SQLite no soporta "ALTER COLUMN DROP NOT NULL": la tabla se RECREA con el
mismo esquema (llanta_id nullable + descripcion), se copian los datos (ids
preservados), se elimina la tabla vieja y se renombra la nueva.

Uso:
    python scripts/migrate_v2_4_0_factura_llanta_nueva.py --dry-run
    python scripts/migrate_v2_4_0_factura_llanta_nueva.py --apply

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

# ── Schema nuevo (llanta_id nullable + descripcion) ──────────────────────

CREATE_FACTURA_LLANTAS_NUEVO = """
CREATE TABLE factura_llantas_nuevo (
    id INTEGER NOT NULL PRIMARY KEY,
    factura_id INTEGER NOT NULL,
    llanta_id INTEGER,
    descripcion VARCHAR(200),
    precio_unitario NUMERIC(12, 2) DEFAULT 0,
    created_at DATETIME
)
"""


# ── Helpers ─────────────────────────────────────────────────────────────

def contar_items(cur: sqlite3.Cursor) -> tuple[int, int]:
    """Devuelve (total_filas, filas_con_llanta_id_null)."""
    cur.execute("SELECT COUNT(*) FROM factura_llantas")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM factura_llantas WHERE llanta_id IS NULL")
    nulos = cur.fetchone()[0]
    return total, nulos


def aplicar_migracion(cur: sqlite3.Cursor) -> None:
    """Recrea factura_llantas con llanta_id nullable + descripcion."""
    # Desactivar FKs durante el rebuild (la tabla se renombra temporalmente)
    cur.execute("PRAGMA foreign_keys=OFF")

    cur.execute(CREATE_FACTURA_LLANTAS_NUEVO)
    cur.execute(
        "INSERT INTO factura_llantas_nuevo "
        "(id, factura_id, llanta_id, descripcion, precio_unitario, created_at) "
        "SELECT id, factura_id, llanta_id, NULL, precio_unitario, created_at "
        "FROM factura_llantas"
    )
    cur.execute("DROP TABLE factura_llantas")
    cur.execute("ALTER TABLE factura_llantas_nuevo RENAME TO factura_llantas")

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
    # Solo importan las violaciones que involucran a factura_llantas (padre o hija).
    relevantes = [v for v in violaciones if "factura_llantas" in (v[0], v[2])]
    if relevantes:
        print(f"  [WARN]   {len(relevantes)} violación(es) de FK sobre factura_llantas: {relevantes[:5]}")
        ok = False
    elif violaciones:
        print(f"  [INFO]   {len(violaciones)} violación(es) de FK preexistentes ajenas a esta migración (ignoradas)")
    else:
        print("  [OK]  Sin violaciones de FK")

    cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='factura_llantas'"
    )
    sql = cur.fetchone()[0]
    print(f"  [INFO]   Esquema final:\n{sql}")
    if "descripcion" not in sql or "llanta_id NOT NULL" in sql:
        print("  [WARN]   factura_llantas no quedó con llanta_id nullable + descripcion")
        ok = False

    if ok:
        print("  [OK]  Verificación completa: BD íntegra, llanta_id nullable + descripcion")
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

            antes_total, antes_nulos = contar_items(cur)
            print(f"\n[ANTES]  factura_llantas: {antes_total} filas ({antes_nulos} con llanta_id NULL)")

            aplicar_migracion(cur)
            conn.commit()

            despues_total, despues_nulos = contar_items(cur)
            print(f"[DESPUÉS] factura_llantas: {despues_total} filas ({despues_nulos} con llanta_id NULL)")

            # Comprobar que los ids se preservaron (muestra)
            cur.execute("SELECT MIN(id), MAX(id) FROM factura_llantas")
            min_id, max_id = cur.fetchone()
            print(f"[INFO]   Rango de ids preservado: {min_id}–{max_id}")

            # Comprobar que ahora se puede insertar con llanta_id NULL + descripcion
            cur.execute(
                "INSERT INTO factura_llantas (id, factura_id, llanta_id, descripcion, precio_unitario) "
                "VALUES (999999, 1, NULL, 'Llanta nueva de prueba', 100)"
            )
            cur.execute("DELETE FROM factura_llantas WHERE id = 999999")
            print("  [OK]  Insert con llanta_id NULL + descripcion permitido")

            ok = verificar(cur)
            print("\n" + ("[OK]  Dry-run exitoso — la migración es segura. Ejecuta --apply." if ok else "[ERROR]  Dry-run detectó problemas."))
            return 0 if ok else 1
        finally:
            conn.close()
            tmp.unlink(missing_ok=True)

    # ── Modo apply: backup + migración real ──
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"delca_pre_v2_4_0_{fecha}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"[BACKUP]  Backup creado: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        antes_total, antes_nulos = contar_items(cur)
        print(f"\n[ANTES]  factura_llantas: {antes_total} filas ({antes_nulos} con llanta_id NULL)")

        aplicar_migracion(cur)
        conn.commit()

        despues_total, despues_nulos = contar_items(cur)
        print(f"[DESPUÉS] factura_llantas: {despues_total} filas ({despues_nulos} con llanta_id NULL)")

        ok = verificar(cur)
        if ok:
            print("\n[OK]  Migración v2.4.0 aplicada correctamente.")
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
        description="Migración v2.4.0 — factura con llanta nueva (item manual)"
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