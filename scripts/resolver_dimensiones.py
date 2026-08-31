"""
Resolvedor de dimensiones de llantas sin catálogo (dimension_id IS NULL).

Vincula las llantas cuyo campo 'dimension' tiene texto (ej. '9.5R17.5')
pero 'dimension_id' quedó NULL, usando el parser ampliado (v2.6.0):
  - Crea el catálogo en dimensiones_llanta si no existe (ancho FLOAT + sufijo)
  - Actualiza llantas.dimension_id

Modos:
    python scripts/resolver_dimensiones.py             # DRY-RUN: simula
    python scripts/resolver_dimensiones.py --ejecutar  # REAL: backup + carga

Seguridades:
    1. Por defecto solo simula (dry-run).
    2. Con --ejecutar crea respaldo de la BD antes de tocar datos.
    3. Solo toca llantas con dimension textual SIN dimension_id.
"""

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import src.database.registry  # noqa: F401

from src.database.base import Base  # noqa: E402
from src.database.engine import DB_PATH, engine, get_session  # noqa: E402

from src.modules.llantas.models.llanta_model import Llanta  # noqa: E402
from src.modules.llantas.models.dimension_llanta_model import DimensionLlanta  # noqa: E402
from scripts.importar_llantas_csv import parsear_dimension  # noqa: E402


def resolver(session, ejecutar: bool) -> dict:
    """Resuelve las dimensiones pendientes. Devuelve conteos."""
    pendientes = session.query(Llanta).filter(
        Llanta.dimension_id.is_(None),
        Llanta.dimension.isnot(None),
        Llanta.dimension != "",
    ).all()

    # Catálogo actual: (ancho, perfil, rin, sufijo) -> id
    dims2id = {
        (d.ancho, d.perfil, d.rin, d.sufijo or ""): d.id
        for d in session.query(DimensionLlanta).all()
    }

    por_crear = {}
    sin_parsear = []
    for ll in pendientes:
        dim_texto = (ll.dimension or "").strip()
        dp = parsear_dimension(dim_texto)
        if dp is None:
            sin_parsear.append((ll.tiquete, dim_texto))
            continue
        if dp not in dims2id:
            por_crear.setdefault(dp, []).append(ll.tiquete)

    print(f"  Llantas pendientes: {len(pendientes)}")
    print(f"  Formatos a crear en catálogo: {len(por_crear)}")
    print(f"  No parseables (quedan sin resolver): {len(sin_parsear)}")
    for tq, dim in sin_parsear[:20]:
        print(f"    [NO PARSE] {tq} -> '{dim}'")
    if len(sin_parsear) > 20:
        print(f"    ... y {len(sin_parsear) - 20} más")

    if not ejecutar:
        print("\n>>> MODO SIMULACION: no se escribe en la BD.")
        print("  Catalogos nuevos que se crearían:")
        for dp, tqs in sorted(por_crear.items(), key=lambda x: (x[0][0] or 0, x[0][1] or 0, x[0][2] or 0)):
            ancho, perfil, rin, sufijo = dp
            print(f"    {ancho} / {perfil} R{rin} {sufijo or ''}  -> {len(tqs)} llantas")
        return {"modo": "dry-run", "pendientes": len(pendientes),
                "por_crear": len(por_crear), "sin_parsear": len(sin_parsear)}

    # ── MODO REAL ──
    from src.core.services.backup_service import create_backup
    ok_bk, msg_bk = create_backup()
    if not ok_bk:
        print(f"[ERROR] No se pudo crear el respaldo: {msg_bk}")
        sys.exit(1)
    print(f"[BACKUP] {msg_bk}")

    Base.metadata.create_all(bind=engine)

    # Crear catálogos faltantes
    creados = 0
    for dp in sorted(por_crear.keys(), key=lambda x: (x[0] or 0, x[1] or 0, x[2] or 0)):
        ancho, perfil, rin, sufijo = dp
        session.add(DimensionLlanta(ancho=ancho, perfil=perfil, rin=rin, sufijo=sufijo or ""))
        creados += 1
    session.flush()

    # Reconstruir índice del catálogo
    dims2id = {
        (d.ancho, d.perfil, d.rin, d.sufijo or ""): d.id
        for d in session.query(DimensionLlanta).all()
    }

    # Actualizar llantas
    vinculadas = 0
    sin_parsear_final = 0
    for ll in pendientes:
        dim_texto = (ll.dimension or "").strip()
        dp = parsear_dimension(dim_texto)
        if dp is None:
            sin_parsear_final += 1
            continue
        dim_id = dims2id.get(dp)
        if dim_id:
            ll.dimension_id = dim_id
            vinculadas += 1

    session.commit()
    return {"modo": "real", "pendientes": len(pendientes),
            "creados": creados, "vinculadas": vinculadas,
            "sin_parsear": sin_parsear_final}


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolver dimensiones de llantas sin catálogo")
    parser.add_argument("--ejecutar", action="store_true",
                        help="Carga real con respaldo previo (por defecto solo simula)")
    args = parser.parse_args()

    print(f"Base de datos: {DB_PATH}\n")
    with get_session() as session:
        resumen = resolver(session, ejecutar=args.ejecutar)

    if resumen["modo"] == "real":
        print(f"\n[RESULTADO] Catálogos creados: {resumen['creados']}")
        print(f"[RESULTADO] Llantas vinculadas: {resumen['vinculadas']}")
        print(f"[RESULTADO] Sin parsear (quedan): {resumen['sin_parsear']}")
    print("\n[OK] Resolución completada.")


if __name__ == "__main__":
    main()