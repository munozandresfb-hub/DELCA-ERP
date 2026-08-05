"""
Migration v2.0.0 — Unificación de conceptos y flujos (estados + ubicaciones).

Transforma los estados y ubicaciones legacy al nuevo modelo definido en
"Unificación de conceptos y flujos":

Estados nuevos:    PENDIENTE, APTA, RECHAZADA, REENCAUCHADA, REPARADA
Ubicaciones nuevas: PRODUCCION, PLANTA, CLIENTE

Uso:
    python scripts/migrate_v2_0_0_unificar_estados_ubicaciones.py --dry-run
    python scripts/migrate_v2_0_0_unificar_estados_ubicaciones.py --apply

--dry-run: ejecuta el mapping completo sobre una COPIA temporal de la BD
           y reporta conteos antes/después. No toca la BD real.
--apply:   hace backup de la BD real en backups/ y aplica la migración.

El mapping nunca es destructivo en contenido: solo reemplaza valores de
estado/ubicación por los equivalentes del nuevo modelo.
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

# ── Mappings ────────────────────────────────────────────────────────────
ESTADO_MAP = {
    "RECIBIDA": "PENDIENTE",
    "INSPECCION": "PENDIENTE",   # aún sin veredicto de inspección inicial
    "EN_PROCESO": "APTA",
    "PRODUCCION": "APTA",
    "LISTA": "REENCAUCHADA",
    "OBSERVADA": "RECHAZADA",
    "ENTREGADA": "REENCAUCHADA",
    "DESPACHADA": "REENCAUCHADA",
}

# Ubicaciones que implican que la llanta salió hacia el cliente
UBICACION_CLIENTE = {"ENTREGA"}

CADENA_PRODUCTIVA = {
    "RECEPCION", "INSPECCION_INICIAL", "RASPADO", "ESCAREO",
    "REPARACION", "CEMENTADO_RELLENO", "EMBANDADO_CORTE",
    "VULCANIZADO", "INSPECCION_FINAL", "PRODUCCION",
}

UBICACION_PLANTA = {"ALMACEN", "BODEGA", "PLANTA"}

# ── Helpers ─────────────────────────────────────────────────────────────

def mapear_ubicacion(ubicacion: str) -> str:
    """Mapea una ubicación legacy al nuevo modelo."""
    u = (ubicacion or "").strip().upper()
    if u in CADENA_PRODUCTIVA:
        return "PRODUCCION"
    if u in UBICACION_PLANTA:
        return "PLANTA"
    if u in UBICACION_CLIENTE:
        return "CLIENTE"
    if u in ("CLIENTE",):
        return "CLIENTE"
    return "PRODUCCION"  # valores desconocidos → PRODUCCION por defecto


def contar_estados(cur: sqlite3.Cursor, tabla: str) -> dict[str, int]:
    col = "estado" if tabla != "ubicaciones_llanta" else "ubicacion"
    cur.execute(f"SELECT {col}, COUNT(*) FROM {tabla} GROUP BY {col}")
    return {r[0]: r[1] for r in cur.fetchall()}


def contar_ubicaciones_llantas(cur: sqlite3.Cursor) -> dict[str, int]:
    cur.execute("SELECT ubicacion_actual, COUNT(*) FROM llantas GROUP BY ubicacion_actual")
    return {r[0]: r[1] for r in cur.fetchall()}


def reportar(titulo: str, antes: dict[str, int], despues: dict[str, int]) -> None:
    print(f"\n{titulo}")
    print(f"  {'Valor legacy':<28} {'Antes':>6} {'→':<4} {'Nuevo':<16} {'Después':>7}")
    for v_legacy, n_antes in sorted(antes.items(), key=lambda x: -x[1]):
        nuevo = mapear_ubicacion(v_legacy) if titulo.startswith("Ubicac") else ESTADO_MAP.get(v_legacy, v_legacy)
        n_despues = despues.get(nuevo, 0)
        print(f"  {v_legacy:<28} {n_antes:>6} {'→':<4} {nuevo:<16} {n_despues:>7}")


def aplicar_migracion(cur: sqlite3.Cursor) -> None:
    """Aplica los mappings de estados y ubicaciones."""
    # 1. Estados en tabla llantas
    for legacy, nuevo in ESTADO_MAP.items():
        cur.execute(
            "UPDATE llantas SET estado = ? WHERE estado = ?",
            (nuevo, legacy),
        )

    # 2. Estados en historial estados_llanta
    for legacy, nuevo in ESTADO_MAP.items():
        cur.execute(
            "UPDATE estados_llanta SET estado = ? WHERE estado = ?",
            (nuevo, legacy),
        )

    # 3. Ubicaciones en historial ubicaciones_llanta
    cur.execute("SELECT DISTINCT ubicacion FROM ubicaciones_llanta")
    ubicaciones = [r[0] for r in cur.fetchall()]
    for u in ubicaciones:
        nuevo = mapear_ubicacion(u)
        if nuevo != u:
            cur.execute(
                "UPDATE ubicaciones_llanta SET ubicacion = ? WHERE ubicacion = ?",
                (nuevo, u),
            )

    # 4. ubicacion_actual en llantas + ajuste estado para las entregadas/despachadas
    cur.execute("SELECT DISTINCT ubicacion_actual FROM llantas")
    ubic_actuales = [r[0] for r in cur.fetchall()]
    for u in ubic_actuales:
        if u is None:
            continue
        nuevo = mapear_ubicacion(u)
        if nuevo != u:
            cur.execute(
                "UPDATE llantas SET ubicacion_actual = ? WHERE ubicacion_actual = ?",
                (nuevo, u),
            )

    # 5. Llantas legacy ENTREGADA/DESPACHADA → ubicación CLIENTE (ya tienen estado REENCAUCHADA)
    cur.execute(
        "UPDATE llantas SET ubicacion_actual = 'CLIENTE' "
        "WHERE estado = 'REENCAUCHADA' AND ubicacion_actual IS NULL"
    )


def verificar(cur: sqlite3.Cursor) -> bool:
    """Verifica que no queden valores legacy y que la BD esté íntegra."""
    ok = True

    cur.execute("SELECT DISTINCT estado FROM llantas")
    estados = {r[0] for r in cur.fetchall()}
    legacy_estados = estados - {"PENDIENTE", "APTA", "RECHAZADA", "REENCAUCHADA", "REPARADA", None}
    if legacy_estados:
        print(f"  [WARN]   Estados legacy restantes en llantas: {legacy_estados}")
        ok = False

    cur.execute("SELECT DISTINCT estado FROM estados_llanta")
    estados_h = {r[0] for r in cur.fetchall()}
    legacy_h = estados_h - {"PENDIENTE", "APTA", "RECHAZADA", "REENCAUCHADA", "REPARADA", None}
    if legacy_h:
        print(f"  [WARN]   Estados legacy restantes en estados_llanta: {legacy_h}")
        ok = False

    cur.execute("SELECT DISTINCT ubicacion FROM ubicaciones_llanta")
    ubi = {r[0] for r in cur.fetchall()}
    legacy_ubi = ubi - {"PRODUCCION", "PLANTA", "CLIENTE", None}
    if legacy_ubi:
        print(f"  [WARN]   Ubicaciones legacy restantes: {legacy_ubi}")
        ok = False

    cur.execute("SELECT DISTINCT ubicacion_actual FROM llantas")
    ubi_a = {r[0] for r in cur.fetchall()}
    legacy_ubi_a = ubi_a - {"PRODUCCION", "PLANTA", "CLIENTE", None}
    if legacy_ubi_a:
        print(f"  [WARN]   ubicacion_actual legacy restantes: {legacy_ubi_a}")
        ok = False

    cur.execute("PRAGMA integrity_check")
    if cur.fetchone()[0] != "ok":
        print("  [WARN]   integrity_check falló")
        ok = False

    if ok:
        print("  [OK]  Verificación completa: sin valores legacy, BD íntegra")
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

            antes_llantas = contar_estados(cur, "llantas")
            antes_historial = contar_estados(cur, "estados_llanta")
            antes_ubi_hist = contar_estados(cur, "ubicaciones_llanta")
            antes_ubi_actual = contar_ubicaciones_llantas(cur)

            aplicar_migracion(cur)
            conn.commit()

            despues_llantas = contar_estados(cur, "llantas")
            despues_historial = contar_estados(cur, "estados_llanta")
            despues_ubi_hist = contar_estados(cur, "ubicaciones_llanta")
            despues_ubi_actual = contar_ubicaciones_llantas(cur)

            print("\n=== RESUMEN DE MIGRACIÓN (simulada) ===")
            reportar("Estados en llantas:", antes_llantas, despues_llantas)
            reportar("Estados en historial (estados_llanta):", antes_historial, despues_historial)
            reportar("Ubicaciones en historial (ubicaciones_llanta):", antes_ubi_hist, despues_ubi_hist)
            reportar("Ubicaciones en llantas.ubicacion_actual:", antes_ubi_actual, despues_ubi_actual)

            ok = verificar(cur)
            print("\n" + ("[OK]  Dry-run exitoso — la migración es segura. Ejecuta --apply." if ok else "[ERROR]  Dry-run detectó problemas."))
            return 0 if ok else 1
        finally:
            conn.close()
            tmp.unlink(missing_ok=True)

    # ── Modo apply: backup + migración real ──
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"delca_pre_v2_0_0_{fecha}.db"
    shutil.copy2(DB_PATH, backup_path)
    print(f"[BACKUP]  Backup creado: {backup_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        antes_llantas = contar_estados(cur, "llantas")
        antes_historial = contar_estados(cur, "estados_llanta")
        antes_ubi_hist = contar_estados(cur, "ubicaciones_llanta")
        antes_ubi_actual = contar_ubicaciones_llantas(cur)

        aplicar_migracion(cur)
        conn.commit()

        despues_llantas = contar_estados(cur, "llantas")
        despues_historial = contar_estados(cur, "estados_llanta")
        despues_ubi_hist = contar_estados(cur, "ubicaciones_llanta")
        despues_ubi_actual = contar_ubicaciones_llantas(cur)

        print("\n=== RESUMEN DE MIGRACIÓN (aplicada) ===")
        reportar("Estados en llantas:", antes_llantas, despues_llantas)
        reportar("Estados en historial (estados_llanta):", antes_historial, despues_historial)
        reportar("Ubicaciones en historial (ubicaciones_llanta):", antes_ubi_hist, despues_ubi_hist)
        reportar("Ubicaciones en llantas.ubicacion_actual:", antes_ubi_actual, despues_ubi_actual)

        ok = verificar(cur)
        if ok:
            print("\n[OK]  Migración v2.0.0 aplicada correctamente.")
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
        description="Migración v2.0.0 — unificación de estados y ubicaciones"
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
