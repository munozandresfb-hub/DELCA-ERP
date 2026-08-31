"""
Migration v2.5.0 — Estado REPROCESO + constraints de estados (flujo correcto 2).

Cambio de esquema:
    1. llantas.estado        → CheckConstraint con 6 estados (agrega REPROCESO)
    2. estados_llanta.estado → CheckConstraint con 6 estados
    3. llantas.ubicacion_actual → DEFAULT 'PLANTA' (antes legacy 'RECEPCION')
    4. Índice ix_llantas_cliente_id (alinea BD con el modelo SQLAlchemy)

SQLite no soporta ALTER para cambiar CHECK/DEFAULT: las tablas se RECREAN con
el nuevo esquema, se copian los datos (ids preservados), se elimina la tabla
vieja y se renombra la nueva. Las FKs de otras tablas quedan intactas porque
los ids no cambian.

Corrección de datos inconsistentes (decisión de negocio):
    - PENDIENTE + PRODUCCION  → APTA + PLANTA (veredicto de inspección)
    - ubicacion_actual NULL   → PLANTA (conservando el estado)

Uso:
    python scripts/migrate_v2_5_0_reproceso.py --dry-run
    python scripts/migrate_v2_5_0_reproceso.py --apply
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

ESTADOS_VALIDOS = ("PENDIENTE", "APTA", "RECHAZADA", "REENCAUCHADA", "REPARADA", "REPROCESO")

# ── Schema nuevo (con CHECK de 6 estados y DEFAULT PLANTA) ────────────────
CREATE_LLANTAS_NUEVO = """
CREATE TABLE llantas_nuevo (
    id INTEGER NOT NULL,
    tiquete VARCHAR NOT NULL,
    marca VARCHAR,
    dimension VARCHAR,
    estado VARCHAR,
    cliente_id INTEGER,
    marca_id INTEGER,
    dimension_id INTEGER,
    diseno_id INTEGER,
    ancho INTEGER,
    perfil INTEGER,
    rin INTEGER,
    indice_carga VARCHAR(10),
    velocidad VARCHAR(5),
    capas VARCHAR(50),
    peso_maximo FLOAT,
    posicion VARCHAR(50),
    rendimiento_km INTEGER,
    costo_produccion FLOAT,
    precio_venta FLOAT,
    numero_orden VARCHAR(100),
    consecutivo VARCHAR(50),
    dot VARCHAR(100),
    observaciones TEXT,
    fecha_ingreso DATETIME,
    ubicacion_actual VARCHAR(50) DEFAULT 'PLANTA',
    asesor VARCHAR(200),
    PRIMARY KEY (id),
    UNIQUE (tiquete),
    CHECK (estado IN ('PENDIENTE','APTA','RECHAZADA','REENCAUCHADA','REPARADA','REPROCESO')),
    FOREIGN KEY(cliente_id) REFERENCES cliente (id)
)
"""

CREATE_ESTADOS_NUEVO = """
CREATE TABLE estados_llanta_nuevo (
    id INTEGER NOT NULL,
    llanta_id INTEGER NOT NULL,
    estado VARCHAR NOT NULL,
    fecha DATETIME,
    PRIMARY KEY (id),
    CHECK (estado IN ('PENDIENTE','APTA','RECHAZADA','REENCAUCHADA','REPARADA','REPROCESO')),
    FOREIGN KEY(llanta_id) REFERENCES llantas (id)
)
"""

COLUMNAS_LLANTAS = [
    "id", "tiquete", "marca", "dimension", "estado", "cliente_id",
    "marca_id", "dimension_id", "diseno_id", "ancho", "perfil", "rin",
    "indice_carga", "velocidad", "capas", "peso_maximo", "posicion",
    "rendimiento_km", "costo_produccion", "precio_venta", "numero_orden",
    "consecutivo", "dot", "observaciones", "fecha_ingreso",
    "ubicacion_actual", "asesor",
]

COLUMNAS_ESTADOS = ["id", "llanta_id", "estado", "fecha"]


def contar_datos(cur: sqlite3.Cursor) -> dict:
    """Reporta el estado actual de los datos inconsistentes."""
    cur.execute(
        "SELECT COUNT(*) FROM llantas WHERE estado='PENDIENTE' "
        "AND ubicacion_actual='PRODUCCION'"
    )
    pendiente_produccion = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM llantas WHERE ubicacion_actual IS NULL"
    )
    sin_ubicacion = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM llantas")
    total = cur.fetchone()[0]
    return {
        "total": total,
        "pendiente_produccion": pendiente_produccion,
        "sin_ubicacion": sin_ubicacion,
    }


def corregir_datos(cur: sqlite3.Cursor) -> None:
    """Corrige las inconsistencias según decisión de negocio."""
    # PENDIENTE + PRODUCCION → APTA + PLANTA (veredicto de inspección aplicado)
    cur.execute(
        "UPDATE llantas SET estado='APTA', ubicacion_actual='PLANTA' "
        "WHERE estado='PENDIENTE' AND ubicacion_actual='PRODUCCION'"
    )
    # ubicacion_actual NULL → PLANTA (ingreso = Planta según flujo correcto 2)
    cur.execute(
        "UPDATE llantas SET ubicacion_actual='PLANTA' "
        "WHERE ubicacion_actual IS NULL"
    )


def aplicar_migracion(cur: sqlite3.Cursor) -> None:
    """Recrea llantas y estados_llanta con CHECK de 6 estados."""
    corregir_datos(cur)

    # Desactivar FKs durante el rebuild
    cur.execute("PRAGMA foreign_keys=OFF")

    # ── Rebuild llantas ──
    cur.execute(CREATE_LLANTAS_NUEVO)
    cols = ", ".join(COLUMNAS_LLANTAS)
    cur.execute(
        f"INSERT INTO llantas_nuevo ({cols}) SELECT {cols} FROM llantas"
    )
    cur.execute("DROP TABLE llantas")
    cur.execute("ALTER TABLE llantas_nuevo RENAME TO llantas")
    cur.execute(
        "CREATE INDEX ix_llantas_cliente_id ON llantas (cliente_id)"
    )

    # ── Rebuild estados_llanta ──
    cur.execute(CREATE_ESTADOS_NUEVO)
    cols_e = ", ".join(COLUMNAS_ESTADOS)
    cur.execute(
        f"INSERT INTO estados_llanta_nuevo ({cols_e}) "
        f"SELECT {cols_e} FROM estados_llanta"
    )
    cur.execute("DROP TABLE estados_llanta")
    cur.execute("ALTER TABLE estados_llanta_nuevo RENAME TO estados_llanta")

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
    relevantes = [
        v for v in violaciones if v[0] in ("llantas", "estados_llanta")
        or v[2] in ("llantas", "estados_llanta")
    ]
    if relevantes:
        print(f"  [WARN]   {len(relevantes)} violación(es) de FK: {relevantes[:5]}")
        ok = False
    elif violaciones:
        print(f"  [INFO]   {len(violaciones)} violación(es) preexistentes ajenas (ignoradas)")
    else:
        print("  [OK]  Sin violaciones de FK")

    # Confirmar que el CHECK de 6 estados existe en ambas tablas
    for tabla in ("llantas", "estados_llanta"):
        cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
        )
        sql = cur.fetchone()[0]
        if "REPROCESO" not in sql:
            print(f"  [WARN]   {tabla} sin REPROCESO en su CHECK")
            ok = False

    # Confirmar que ya no hay estados legacy
    cur.execute("SELECT DISTINCT estado FROM llantas")
    estados = {r[0] for r in cur.fetchall()}
    legacy = estados - set(ESTADOS_VALIDOS)
    if legacy:
        print(f"  [WARN]   Estados legacy en llantas: {legacy}")
        ok = False

    # Confirmar que no quedan ubicaciones inconsistentes
    cur.execute(
        "SELECT COUNT(*) FROM llantas WHERE estado='PENDIENTE' "
        "AND ubicacion_actual='PRODUCCION'"
    )
    if cur.fetchone()[0]:
        print("  [WARN]   Quedan PENDIENTE+PRODUCCION")
        ok = False
    cur.execute("SELECT COUNT(*) FROM llantas WHERE ubicacion_actual IS NULL")
    if cur.fetchone()[0]:
        print("  [WARN]   Quedan ubicaciones NULL")
        ok = False

    if ok:
        print("  [OK]  Verificación completa: constraints aplicados, datos íntegros")
    return ok


def run(dry_run: bool) -> int:
    if not DB_PATH.exists():
        print(f"[ERROR]  No existe la BD en {DB_PATH}")
        return 1

    # ── Modo dry-run ──
    if dry_run:
        tmp = PROJECT_ROOT / "delca_migracion_prueba.db"
        shutil.copy2(DB_PATH, tmp)
        print(f"[INFO]  MODO DRY-RUN — probando sobre copia temporal: {tmp.name}")
        conn = sqlite3.connect(tmp)
        try:
            cur = conn.cursor()
            antes = contar_datos(cur)
            print(f"\n[ANTES]  llantas: {antes['total']} | "
                  f"PENDIENTE+PRODUCCION: {antes['pendiente_produccion']} | "
                  f"sin ubicación: {antes['sin_ubicacion']}")

            aplicar_migracion(cur)
            conn.commit()

            despues = contar_datos(cur)
            print(f"[DESPUÉS] llantas: {despues['total']} | "
                  f"PENDIENTE+PRODUCCION: {despues['pendiente_produccion']} | "
                  f"sin ubicación: {despues['sin_ubicacion']}")

            cur.execute("SELECT MIN(id), MAX(id) FROM llantas")
            min_id, max_id = cur.fetchone()
            print(f"[INFO]   Rango de ids llantas preservado: {min_id}–{max_id}")

            ok = verificar(cur)
            print("\n" + ("[OK]  Dry-run exitoso — la migración es segura. Ejecuta --apply."
                          if ok else "[ERROR]  Dry-run detectó problemas."))
            return 0 if ok else 1
        finally:
            conn.close()
            tmp.unlink(missing_ok=True)

    # ── Modo apply ──
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"delca_pre_v2_5_0_{fecha}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"[BACKUP]  Backup creado: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        antes = contar_datos(cur)
        print(f"\n[ANTES]  llantas: {antes['total']} | "
              f"PENDIENTE+PRODUCCION: {antes['pendiente_produccion']} | "
              f"sin ubicación: {antes['sin_ubicacion']}")

        aplicar_migracion(cur)
        conn.commit()

        despues = contar_datos(cur)
        print(f"[DESPUÉS] llantas: {despues['total']} | "
              f"PENDIENTE+PRODUCCION: {despues['pendiente_produccion']} | "
              f"sin ubicación: {despues['sin_ubicacion']}")

        ok = verificar(cur)
        if ok:
            print("\n[OK]  Migración v2.5.0 aplicada correctamente.")
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
    """Función idempotente para el mecanismo run_migration_once de main.py.

    Verifica si la BD ya tiene el CHECK de 6 estados; si es así, no hace nada
    (ya fue aplicada vía --apply o manualmente). Si no, aplica el rebuild con
    backup previo.
    """
    if not DB_PATH.exists():
        print("[migracion] delca.db no encontrado — saltando.")
        return True

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        # ── Idempotencia: ¿ya tiene CHECK con REPROCESO? ──
        cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='llantas'"
        )
        fila = cur.fetchone()
        if fila and fila[0] and "REPROCESO" in fila[0]:
            print("[OK] CHECK de 6 estados ya aplicado en llantas — saltando.")
            return True

        # ── Backup + aplicar ──
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"delca_pre_v2_5_0_{fecha}.db"
        shutil.copy2(DB_PATH, backup_path)
        print(f"[BACKUP]  Backup creado: {backup_path}")

        corregir_datos(cur)
        aplicar_migracion(cur)
        conn.commit()

        ok = verificar(cur)
        if not ok:
            conn.rollback()
            print("[ERROR]  Verificación falló — migración v2.5.0 no aplicada")
            return False
        print("[OK]  Migración v2.5.0 aplicada correctamente (run_migration)")
        return True
    except Exception as e:
        conn.rollback()
        print(f"[ERROR]  Migración v2.5.0 falló: {e}")
        return False
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migración v2.5.0 — estado REPROCESO + constraints (flujo correcto 2)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simular la migración sobre una copia temporal (sin tocar la BD real)",
    )
    parser.add_argument(
        "--apply", action="store_true",
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