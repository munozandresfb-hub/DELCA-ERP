"""
Importador de marcas de llanta desde CSV a la base de datos del DELCA.

Lee el archivo 'Marcas 18-08.csv' (generado por el ETL de migracion desde
MAE_MARCA.DBF) y lo inserta en la tabla 'marcas_llanta'.

Modos de ejecucion:
    python scripts/importar_marcas_csv.py                # DRY-RUN: simula, no escribe
    python scripts/importar_marcas_csv.py --ejecutar     # REAL: respaldo + carga

Logica de carga:
    1. Omite marcas cuyo nombre ya existe en la BD (comparacion sin
       distinguir mayusculas: 'GOODYEAR' == 'GoodYear').
    2. Si la sigla del CSV ya esta usada por OTRA marca en la BD, la
       inserta con sigla NULL (evita violar el UNIQUE) y lo reporta.
    3. Con --ejecutar crea un respaldo de la BD antes de cargar.
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
from src.modules.llantas.models.marca_llanta_model import MarcaLlanta  # noqa: E402

CSV_DEFAULT = Path(r"C:\Users\andre\OneDrive\Escritorio\DELCA\Marcas 18-08.csv")


# ======================================================================
#  Lectura
# ======================================================================

def leer_csv(path: Path) -> list[dict]:
    if not path.exists():
        print(f"[ERROR] No se encuentra el archivo: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# ======================================================================
#  Carga
# ======================================================================

def cargar(filas: list[dict], ejecutar: bool) -> dict:
    # ── Preparar ────────────────────────────────────────────────
    preparadas = []
    invalidas = []
    for fila in filas:
        nombre = (fila.get("nombre") or "").strip()
        siglas = (fila.get("siglas") or "").strip() or None
        if not nombre:
            invalidas.append((fila.get("codigo_origen", ""), "nombre vacio"))
            continue
        preparadas.append({"nombre": nombre, "siglas": siglas})

    # ── DRY-RUN ─────────────────────────────────────────────────
    if not ejecutar:
        print(">>> MODO SIMULACION (dry-run): NO se escribe en la base de datos.\n")
        print(f"Base de datos: {DB_PATH}")
        print(f"Filas leidas del CSV: {len(filas)}")
        print(f"  Validas (se insertarian): {len(preparadas)}")
        print(f"  Invalidas (omitidas): {len(invalidas)}")
        for cod, motivo in invalidas[:10]:
            print(f"    [INVALIDA] {cod} -> {motivo}")

        with get_session() as session:
            bd = session.query(MarcaLlanta).all()
        nombres_bd = {m.nombre.lower() for m in bd}
        siglas_bd = {m.siglas: m.nombre for m in bd if m.siglas is not None}

        a_insertar, ya_existen, colision = [], [], []
        for p in preparadas:
            if p["nombre"].lower() in nombres_bd:
                ya_existen.append(p)
            elif p["siglas"] and p["siglas"] in siglas_bd:
                colision.append((p, siglas_bd[p["siglas"]]))
                a_insertar.append({**p, "siglas": None})
            else:
                a_insertar.append(p)

        print(f"  NUEVAS a insertar: {len(a_insertar)}")
        print(f"  Ya existen en BD (se omiten): {len(ya_existen)}")
        print(f"  Colision de siglas (se insertan con sigla NULL): {len(colision)}")
        for p, dueno in colision:
            print(f"    [COLISION] {p['nombre']} queria siglas '{p['siglas']}' (usada por {dueno}) -> sigla NULL")
        print("\n[OK] Simulacion completada. Use --ejecutar para cargar de verdad.")
        return {"modo": "dry-run", "nuevas": len(a_insertar)}

    # ── MODO REAL ───────────────────────────────────────────────
    print(">>> MODO REAL: se escribira en la base de datos.\n")

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

    Base.metadata.create_all(bind=engine)

    insertadas, omitidas, sin_siglas = 0, [], []
    with get_session() as session:
        bd = session.query(MarcaLlanta).all()
        nombres_bd = {m.nombre.lower() for m in bd}
        siglas_bd = {m.siglas for m in bd if m.siglas is not None}

        for p in preparadas:
            if p["nombre"].lower() in nombres_bd:
                omitidas.append(p["nombre"])
                continue
            siglas = p["siglas"]
            if siglas and siglas in siglas_bd:
                sin_siglas.append((p["nombre"], siglas))
                siglas = None
            session.add(MarcaLlanta(nombre=p["nombre"], siglas=siglas))
            nombres_bd.add(p["nombre"].lower())
            if siglas:
                siglas_bd.add(siglas)
            insertadas += 1

    print(f"[CARGA] Marcas insertadas: {insertadas}")
    print(f"[CARGA] Omitidas (ya existian): {len(omitidas)}")
    for n in omitidas[:10]:
        print(f"    [OMITIDA] {n}")
    print(f"[CARGA] Insertadas con sigla NULL (colision): {len(sin_siglas)}")
    for n, s in sin_siglas:
        print(f"    [SIN SIGLA] {n} (sigla '{s}' ya en uso)")

    with get_session() as session:
        total = session.query(MarcaLlanta).count()
    print(f"\n[OK] Carga completada. Total de marcas en la BD: {total}")
    return {"modo": "real", "insertadas": insertadas, "omitidas": len(omitidas)}


# ======================================================================
#  Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Importar marcas de llanta desde CSV al DELCA")
    parser.add_argument(
        "--ejecutar",
        action="store_true",
        help="Carga real con respaldo previo (por defecto solo simula)",
    )
    parser.add_argument("--csv", default=str(CSV_DEFAULT), help="Ruta del CSV a importar")
    args = parser.parse_args()

    filas = leer_csv(Path(args.csv))
    cargar(filas, ejecutar=args.ejecutar)


if __name__ == "__main__":
    main()