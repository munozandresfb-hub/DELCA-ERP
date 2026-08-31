"""
Importador de llantas desde CSV a la base de datos del DELCA.

Lee 'Llantas 18-08.csv' (generado por el ETL de MAE_PROD.DBF) y lo inserta en
la tabla 'llantas', creando antes los catalogos faltantes (marcas, dimensiones,
disenos) y los historicos iniciales (estados_llanta, ubicaciones_llanta).

Modos de ejecucion:
    python scripts/importar_llantas_csv.py                 # DRY-RUN: simula, no escribe
    python scripts/importar_llantas_csv.py --ejecutar      # REAL: respaldo + carga

Seguridades:
    1. Por defecto solo simula (dry-run) y reporta lo que se insertaria.
    2. Con --ejecutar crea un respaldo de la BD antes de cargar.
    3. Nunca duplica: si el tiquete ya existe en la BD, lo omite y lo reporta.
    4. Los catalogos (marcas/dimensiones/disenos) se crean antes de las llantas
       y solo si faltan (nombre/sigla unicos).
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

from src.modules.llantas.models.llanta_model import Llanta  # noqa: E402
from src.modules.llantas.models.marca_llanta_model import MarcaLlanta  # noqa: E402
from src.modules.llantas.models.dimension_llanta_model import DimensionLlanta  # noqa: E402
from src.modules.llantas.models.diseno_llanta_model import DisenoLlanta  # noqa: E402
from src.modules.llantas.models.estado_llanta_model import EstadoLlanta  # noqa: E402
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta  # noqa: E402
from src.modules.llantas.services.llanta_service._constantes import (  # noqa: E402
    COMBINACIONES_VALIDAS,
)

# Ruta del CSV generado por el ETL (carpeta DELCA del Escritorio)
CSV_DEFAULT = Path(r"C:\Users\andre\OneDrive\Escritorio\DELCA\Llantas 18-08.csv")

# Archivo de salida con las llantas rechazadas por combinación inválida
RECHAZADAS_DEFAULT = Path(r"C:\Users\andre\OneDrive\Escritorio\DELCA\llantas no migradas.csv")

# Tipo de diseno por convencion: REPARADA usa diseno "REP"
DISENO_REPARADA = "REP"


def es_combinacion_valida(estado: str | None, ubicacion: str | None) -> bool:
    """¿La combinación estado+ubicación es válida según el flujo correcto 2?

    Reglas R1-R6 (COMBINACIONES_VALIDAS). Si la llanta no trae ubicación
    asignada, se considera válida (se inserta con ubicación NULL).
    """
    est = (estado or "PENDIENTE").strip() or "PENDIENTE"
    ubi = (ubicacion or "").strip()
    if not ubi:
        return True
    return ubi in COMBINACIONES_VALIDAS.get(est, set())


def escribir_rechazadas(filas: list[dict], headers: list[str], ruta: Path) -> int:
    """Escribe las llantas rechazadas en el archivo 'llantas no migradas.csv'.

    Devuelve el número de filas escritas (0 si no hay rechazadas).
    """
    if not filas:
        return 0
    with open(ruta, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=headers)
        writer.writeheader()
        writer.writerows(filas)
    return len(filas)


def parsear_dimension(dim: str) -> tuple | None:
    """Parsea una dimensión de llanta.

    Retorna (ancho, perfil, rin, sufijo) o None si no es parseable.
    El sufijo (C, U, etc.) se conserva visible en la dimensión.

    Formatos soportados:
      - Métrico:       295/80R22.5, 215/75R16C, 9.5R17.5, 7.50R16
      - Convencional:  10.00-20, 12-22.5, 7.50-16U
      - Flotación:     31X10.50R15
      - Especial:      H78-15 (perfil None, rin 15)
    """
    import re
    d = (dim or "").strip()

    # Extraer sufijo de letras final (C, U, etc.) — visible en la dimensión
    m_suf = re.search(r"([A-Za-z]+)$", d)
    sufijo = ""
    cuerpo = d
    if m_suf:
        sufijo = m_suf.group(1)
        cuerpo = d[: m_suf.start()].strip()

    # 1) Métrico: ancho[/perfil] R rin  (ancho puede ser decimal: 9.5, 7.50)
    m = re.match(
        r"^(\d+(?:\.\d+)?)(?:/(\d{2}))?\s*[Rr]\s*(\d+(?:\.\d+)?)$",
        cuerpo,
    )
    if m:
        ancho = float(m.group(1))
        perfil = int(m.group(2)) if m.group(2) else None
        rin = float(m.group(3))
        return ancho, perfil, rin, sufijo

    # 1b) Métrico con guion en vez de R: 215/75-15
    m1b = re.match(
        r"^(\d+(?:\.\d+)?)/(\d{2})\s*[-]\s*(\d+(?:\.\d+)?)$",
        cuerpo,
    )
    if m1b:
        ancho = float(m1b.group(1))
        perfil = int(m1b.group(2))
        rin = float(m1b.group(3))
        return ancho, perfil, rin, sufijo

    # 2) Convencional: ancho[-/ ]rin  (rin puede ser decimal: 12-22.5)
    m2 = re.match(r"^(\d+\.?\d*)[\s\-/](\d+\.?\d*)$", cuerpo)
    if m2:
        ancho = float(m2.group(1))
        rin = float(m2.group(2))
        return ancho, None, rin, sufijo

    # 3) Flotación: diámetro X ancho R rin  (31X10.50R15)
    m3 = re.match(r"^(\d{2})[Xx](\d+\.?\d*)[Rr](\d+(?:\.\d+)?)$", cuerpo)
    if m3:
        ancho = float(m3.group(2))  # ancho real de la banda
        rin = float(m3.group(3))
        return ancho, None, rin, sufijo

    # 4) Especial: letra+serie-rin  (H78-15)
    m4 = re.match(r"^[A-Za-z]\d{2}[\s\-/](\d+(?:\.\d+)?)$", cuerpo)
    if m4:
        rin = float(m4.group(1))
        return None, None, rin, sufijo

    return None


# ======================================================================
#  Lectura del CSV
# ======================================================================

def leer_csv(path: Path) -> list[dict]:
    """Lee el CSV (UTF-8 BOM) y devuelve las filas como dicts."""
    if not path.exists():
        print(f"[ERROR] No se encuentra el archivo: {path}")
        sys.exit(1)
    filas = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for fila in csv.DictReader(fh):
            filas.append(fila)
    return filas


# ======================================================================
#  Catalogos
# ======================================================================

def preparar_catalogos(session) -> tuple[dict, dict, dict]:
    """
    Resuelve/crea los catalogos necesarios.
    Devuelve: (siglas->id, (ancho,perfil,rin)->id, nombre_diseno->id)
    """
    siglas2id = {m.siglas.strip().upper(): m.id for m in session.query(MarcaLlanta).all() if m.siglas}
    dims2id = {
        (d.ancho, d.perfil, d.rin, d.sufijo or ""): d.id
        for d in session.query(DimensionLlanta).all()
    }
    disenos2id = {d.nombre.strip(): d.id for d in session.query(DisenoLlanta).all()}
    return siglas2id, dims2id, disenos2id


# ======================================================================
#  Carga
# ======================================================================

def cargar(filas: list[dict], ejecutar: bool) -> dict:
    """
    Inserta las llantas en la BD.

    ejecutar=False -> solo cuenta lo que se insertaria (dry-run).
    ejecutar=True  -> crea respaldo y carga de verdad.
    """
    # ── Preparar datos ──────────────────────────────────────────
    preparadas = []
    rechazadas = []
    invalidas = []
    for fila in filas:
        tiquete = (fila.get("tiquete") or "").strip()
        if not tiquete:
            invalidas.append(("", "tiquete vacio"))
            continue
        # Rechazar combinaciones estado+ubicación inválidas (reglas R1-R6)
        if not es_combinacion_valida(
            fila.get("estado"), fila.get("ubicacion_actual")
        ):
            rechazadas.append(fila)
            continue
        preparadas.append(fila)

    # ── DRY-RUN: no toca la BD ──────────────────────────────────
    if not ejecutar:
        print(">>> MODO SIMULACION (dry-run): NO se escribe en la base de datos.\n")
        print(f"Base de datos: {DB_PATH}")
        print(f"Filas leidas del CSV: {len(filas)}")
        print(f"  Validas (se insertarian): {len(preparadas)}")
        print(f"  Rechazadas (combinacion invalida R1-R6): {len(rechazadas)}")
        print(f"  Invalidas (omitidas): {len(invalidas)}")

        # Generar archivo de rechazadas (también en dry-run para revisión)
        headers = list(filas[0].keys()) if filas else []
        n_archivo = escribir_rechazadas(rechazadas, headers, RECHAZADAS_DEFAULT)
        if n_archivo:
            print(f"  Archivo generado: {RECHAZADAS_DEFAULT.name} ({n_archivo} filas)")

        with get_session() as session:
            siglas2id, dims2id, disenos2id = preparar_catalogos(session)

            # Catalogos a crear
            marcas_falt = set()
            dims_falt = set()
            disenos_falt = set()
            for p in preparadas:
                marca = (p.get("marca") or "").strip()
                dimension = (p.get("dimension") or "").strip()
                banda = (p.get("banda") or "").strip()
                if marca and marca.upper() not in siglas2id:
                    marcas_falt.add(marca.upper())
                # Dimension: si viene dimension_id vacio pero hay texto, hay que crearla
                if dimension and not (p.get("dimension_id") or ""):
                    dp = parsear_dimension(dimension)
                    if dp and dp not in dims2id:
                        dims_falt.add(dp)
                if banda and banda.strip() not in disenos2id:
                    disenos_falt.add(banda.strip())

            # Tiquetes ya en BD
            tiquetes_bd = {t for (t,) in session.query(Llanta.tiquete).all()}
            duplicados = sum(1 for p in preparadas if p["tiquete"] in tiquetes_bd)
            nuevos = len(preparadas) - duplicados

        print(f"\n--- CATALOGOS NECESARIOS ---")
        print(f"  Marcas a crear: {len(marcas_falt)}")
        print(f"  Dimensiones a crear: {len(dims_falt)}")
        print(f"  Disenos a crear: {len(disenos_falt)}")
        print(f"\n  Tiquetes que ya existen en la BD (se omitirian): {duplicados}")
        print(f"  Tiquetes nuevos que se insertarian: {nuevos}")
        print("\n[OK] Simulacion completada. Use --ejecutar para cargar de verdad.")
        return {"modo": "dry-run", "preparados": len(preparadas)}

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

    # 2b) Generar archivo de llantas rechazadas (combinación inválida)
    headers = list(filas[0].keys()) if filas else []
    n_rechazadas = escribir_rechazadas(rechazadas, headers, RECHAZADAS_DEFAULT)
    if n_rechazadas:
        print(f"[RECHAZADAS] Archivo generado: {RECHAZADAS_DEFAULT.name} ({n_rechazadas} filas)")
    else:
        print("[RECHAZADAS] No hay llantas rechazadas por combinación inválida")

    # 3) Cargar
    insertadas = 0
    omitidas = 0
    creadas = {"marcas": 0, "dimensiones": 0, "disenos": 0}

    with get_session() as session:
        siglas2id, dims2id, disenos2id = preparar_catalogos(session)

        # ── 3a) Crear catalogos faltantes ───────────────────────
        marcas_por_crear = set()
        dims_por_crear = set()
        disenos_por_crear = set()
        for p in preparadas:
            marca = (p.get("marca") or "").strip()
            dimension = (p.get("dimension") or "").strip()
            banda = (p.get("banda") or "").strip()
            if marca and marca.upper() not in siglas2id:
                marcas_por_crear.add(marca.upper())
            if dimension and not (p.get("dimension_id") or ""):
                dp = parsear_dimension(dimension)
                if dp and dp not in dims2id:
                    dims_por_crear.add(dp)
            if banda and banda.strip() not in disenos2id:
                disenos_por_crear.add(banda.strip())

        for sigla in sorted(marcas_por_crear):
            nombre = sigla.capitalize()
            m = MarcaLlanta(nombre=nombre, siglas=sigla)
            session.add(m)
            creadas["marcas"] += 1
        session.flush()
        siglas2id = {m.siglas.strip().upper(): m.id for m in session.query(MarcaLlanta).all() if m.siglas}

        for ancho, perfil, rin, sufijo in sorted(
            dims_por_crear, key=lambda d: (d[0] or 0, d[1] or 0, d[2] or 0, d[3] or "")
        ):
            d = DimensionLlanta(ancho=ancho, perfil=perfil, rin=rin, sufijo=sufijo or "")
            session.add(d)
            creadas["dimensiones"] += 1
        session.flush()
        dims2id = {
            (d.ancho, d.perfil, d.rin, d.sufijo or ""): d.id
            for d in session.query(DimensionLlanta).all()
        }

        for nombre_d in sorted(disenos_por_crear):
            tipo = "MIXTO"
            if nombre_d.upper() == DISENO_REPARADA:
                tipo = "MIXTO"
            d = DisenoLlanta(nombre=nombre_d, tipo=tipo)
            session.add(d)
            creadas["disenos"] += 1
        session.flush()
        disenos2id = {d.nombre.strip(): d.id for d in session.query(DisenoLlanta).all()}

        # ── 3b) Insertar llantas ────────────────────────────────
        tiquetes_bd = {t for (t,) in session.query(Llanta.tiquete).all()}

        for p in preparadas:
            tiquete = p["tiquete"]
            if tiquete in tiquetes_bd:
                omitidas += 1
                continue

            marca = (p.get("marca") or "").strip()
            dimension = (p.get("dimension") or "").strip()
            banda = (p.get("banda") or "").strip()

            # Resolver catalogos
            marca_id = siglas2id.get(marca.upper()) if marca else None
            dimension_id = None
            if p.get("dimension_id"):
                dimension_id = int(p["dimension_id"])
            elif dimension:
                dp = parsear_dimension(dimension)
                if dp:
                    dimension_id = dims2id.get(dp)
            diseno_id = disenos2id.get(banda.strip()) if banda else None

            llanta = Llanta(
                tiquete=tiquete,
                numero_orden=(p.get("numero_orden") or "").strip() or None,
                consecutivo=(p.get("consecutivo") or "").strip() or None,
                observaciones=(p.get("observaciones") or "").strip() or None,
                fecha_ingreso=(
                    __import__("datetime").datetime.fromisoformat(p["fecha_ingreso"])
                    if p.get("fecha_ingreso") else None
                ),
                marca=marca or None,
                dimension=dimension or None,
                marca_id=marca_id,
                dimension_id=dimension_id,
                diseno_id=diseno_id,
                costo_produccion=(
                    float(p["costo_produccion"]) if p.get("costo_produccion") not in (None, "") else None
                ),
                precio_venta=(
                    float(p["precio_venta"]) if p.get("precio_venta") not in (None, "") else None
                ),
                asesor=(p.get("asesor") or "").strip() or None,
                estado=(p.get("estado") or "PENDIENTE").strip(),
                ubicacion_actual=(p.get("ubicacion_actual") or "").strip() or None,
                cliente_id=int(p["cliente_id"]) if p.get("cliente_id") else None,
            )
            session.add(llanta)
            session.flush()  # obtener llanta.id

            # Historico inicial de estado (fecha = fecha_ingreso real de la llanta)
            fecha_hist = llanta.fecha_ingreso or (
                __import__("datetime").datetime.now()
            )
            session.add(EstadoLlanta(
                llanta_id=llanta.id,
                estado=llanta.estado,
                fecha=fecha_hist,
            ))
            # Historico inicial de ubicacion
            if llanta.ubicacion_actual:
                session.add(UbicacionLlanta(
                    llanta_id=llanta.id,
                    ubicacion=llanta.ubicacion_actual,
                    fecha=fecha_hist,
                ))

            tiquetes_bd.add(tiquete)
            insertadas += 1

    # 4) Verificar
    with get_session() as session:
        total = session.query(Llanta).count()
    print(f"[CATALOGOS] Marcas creadas: {creadas['marcas']} | Dimensiones: {creadas['dimensiones']} | Disenos: {creadas['disenos']}")
    print(f"[CARGA] Llantas insertadas: {insertadas}")
    print(f"[CARGA] Tiquetes omitidos (ya existian): {omitidas}")
    print(f"\n[OK] Carga completada. Total de llantas en la BD: {total}")
    return {"modo": "real", "insertadas": insertadas, "omitidas": omitidas}


# ======================================================================
#  Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Importar llantas desde CSV al DELCA")
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