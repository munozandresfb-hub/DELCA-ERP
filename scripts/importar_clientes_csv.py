"""
Importador de clientes desde CSV a la base de datos del DELCA.

Lee el archivo 'Clientes 1 18-08.csv' (generado por el ETL de migracion)
y lo inserta en la tabla 'cliente' del sistema.

Modos de ejecucion:
    python scripts/importar_clientes_csv.py                # DRY-RUN: simula, no escribe
    python scripts/importar_clientes_csv.py --ejecutar     # REAL: respaldo + carga

Seguridades:
    1. Por defecto solo simula (dry-run) y reporta lo que se insertaria.
    2. Con --ejecutar crea un respaldo de la BD antes de cargar.
    3. Nunca duplica: si el NIT ya existe en la BD, lo omite y lo reporta.
"""

import argparse
import csv
import sys
from pathlib import Path

# ── Asegurar que el proyecto esta en el path ────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# ── Registrar modelos ANTES de cualquier operacion de BD ────────────
import src.database.registry  # noqa: F401

from src.database.base import Base  # noqa: E402
from src.database.engine import DB_PATH, engine, get_session  # noqa: E402
from src.modules.clientes.models.cliente_model import Cliente  # noqa: E402

# Ruta del CSV generado por el ETL (carpeta DELCA del Escritorio)
CSV_DEFAULT = Path(
    r"C:\Users\andre\OneDrive\Escritorio\DELCA\Clientes 1 18-08.csv"
)


# ======================================================================
#  Lectura y validacion del CSV
# ======================================================================

def leer_csv(path: Path) -> list[dict]:
    """Lee el CSV (UTF-8 BOM) y devuelve las filas como dicts."""
    if not path.exists():
        print(f"[ERROR] No se encuentra el archivo: {path}")
        sys.exit(1)

    filas = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for fila in reader:
            filas.append(fila)
    return filas


def validar_fila(fila: dict) -> tuple[bool, str]:
    """Valida una fila del CSV. Devuelve (ok, motivo_error)."""
    nombre = (fila.get("nombre") or "").strip()
    nit = (fila.get("nit") or "").strip()
    if not nombre:
        return False, "nombre vacio"
    if not nit:
        return False, "NIT vacio"
    return True, ""


# ======================================================================
#  Carga
# ======================================================================

def _nits_en_bd(session) -> set[str]:
    """Conjunto de NITs ya existentes en la tabla cliente."""
    return {c.nit for c in session.query(Cliente.nit).all()}


def cargar(filas: list[dict], ejecutar: bool) -> dict:
    """
    Inserta los clientes en la BD.

    ejecutar=False -> solo cuenta lo que se insertaria (dry-run).
    ejecutar=True  -> crea respaldo y carga de verdad.
    """
    # ── Preparar datos ──────────────────────────────────────────
    preparados = []
    invalidados = []
    for fila in filas:
        ok, motivo = validar_fila(fila)
        if not ok:
            invalidados.append((fila.get("nombre", ""), motivo))
        preparados.append({
            "nombre": fila["nombre"].strip(),
            "nit": fila["nit"].strip(),
            "telefono": (fila.get("telefono") or "").strip() or None,
            "celular": (fila.get("celular") or "").strip() or None,
            "email": (fila.get("email") or "").strip() or None,
            "direccion": (fila.get("direccion") or "").strip() or None,
        })

    # ── DRY-RUN: no toca la BD ──────────────────────────────────
    if not ejecutar:
        print(">>> MODO SIMULACION (dry-run): NO se escribe en la base de datos.\n")
        print(f"Base de datos: {DB_PATH}")
        print(f"Filas leidas del CSV: {len(filas)}")
        print(f"  Validas (se insertarian): {len(preparados)}")
        print(f"  Invalidas (omitidas): {len(invalidados)}")
        for nombre, motivo in invalidados[:10]:
            print(f"    [INVALIDA] {nombre} -> {motivo}")
        if len(invalidados) > 10:
            print(f"    ... y {len(invalidados) - 10} mas")

        # Ver NITs que ya existen en BD (sin insertar nada)
        with get_session() as session:
            nits_bd = _nits_en_bd(session)
        duplicados_bd = sum(1 for p in preparados if p["nit"] in nits_bd)
        print(f"  NITs que ya existen en la BD (se omitirian): {duplicados_bd}")
        print(f"  NITs nuevos que se insertarian: {len(preparados) - duplicados_bd}")
        print("\n[OK] Simulacion completada. Use --ejecutar para cargar de verdad.")
        return {"modo": "dry-run", "preparados": len(preparados)}

    # ── MODO REAL: respaldo + carga ─────────────────────────────
    print(">>> MODO REAL: se escribira en la base de datos.\n")

    # 1) Respaldo previo
    try:
        from src.core.services.backup_service import create_backup
        ok_bk, msg_bk = create_backup()
    except Exception as e:
        ok_bk, msg_bk = False, f"Backup no disponible: {e}"
    if not ok_bk:
        print(f"[ERROR] No se pudo crear el respaldo: {msg_bk}")
        print("Abortando carga para no tocar la BD sin respaldo.")
        sys.exit(1)
    print(f"[BACKUP] {msg_bk}")

    # 2) Crear tablas si no existen
    Base.metadata.create_all(bind=engine)

    # 3) Cargar
    insertados, omitidos = 0, []
    with get_session() as session:
        nits_bd = _nits_en_bd(session)
        for p in preparados:
            if p["nit"] in nits_bd:
                omitidos.append(p["nit"])
                continue
            cliente = Cliente(**p)
            session.add(cliente)
            nits_bd.add(p["nit"])
            insertados += 1
    # (get_session hace commit al salir)

    print(f"[CARGA] Clientes insertados: {insertados}")
    print(f"[CARGA] NITs omitidos (ya existian): {len(omitidos)}")
    for nit in omitidos[:10]:
        print(f"    [OMITIDO] NIT {nit} ya existe en la BD")
    if len(omitidos) > 10:
        print(f"    ... y {len(omitidos) - 10} mas")

    # 4) Verificar
    with get_session() as session:
        total = session.query(Cliente).count()
    print(f"\n[OK] Carga completada. Total de clientes en la BD: {total}")
    return {"modo": "real", "insertados": insertados, "omitidos": len(omitidos)}


# ======================================================================
#  Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Importar clientes desde CSV al DELCA")
    parser.add_argument(
        "--ejecutar",
        action="store_true",
        help="Carga real con respaldo previo (por defecto solo simula)",
    )
    parser.add_argument(
        "--csv",
        default=str(CSV_DEFAULT),
        help="Ruta del CSV a importar",
    )
    args = parser.parse_args()

    filas = leer_csv(Path(args.csv))
    cargar(filas, ejecutar=args.ejecutar)


if __name__ == "__main__":
    main()