"""
Unificador de diseños duplicados por normalización de nombre.

El CSV legacy trae diseños con guion (DV-RT4, DV-RT2, PBT14-W) que el
importador creó como registros NUEVOS en disenos_llanta, mientras que el
catálogo canónico ya tenía el mismo diseño SIN guion (DVRT4, DVRT2, PBT14W)
con precios. Esto dejó llantas apuntando al duplicado (sin precios).

Este script:
  1. Reasigna llantas.diseno_id del duplicado → canónico.
  2. Reasigna precios_producto.diseno_id del duplicado → canónico (si los hay).
  3. Elimina el duplicado de disenos_llanta.

Mapeo (por normalización: quitar guiones/espacios, mayúsculas):
    DV-RT4  -> DVRT4
    DV-RT2  -> DVRT2
    PBT14-W -> PBT14W

Modos:
    python scripts/unificar_disenos.py             # DRY-RUN: simula
    python scripts/unificar_disenos.py --ejecutar  # REAL: backup + aplica
"""

import argparse
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import src.database.registry  # noqa: F401

from src.database.engine import DB_PATH, get_session  # noqa: E402

from src.modules.llantas.models.diseno_llanta_model import DisenoLlanta  # noqa: E402
from src.modules.llantas.models.llanta_model import Llanta  # noqa: E402
from src.modules.inventario.models.precio_producto_model import PrecioProducto  # noqa: E402


def normalizar(nombre: str) -> str:
    """Quita guiones/espacios/puntos y pasa a mayúsculas: DV-RT4 -> DVRT4."""
    return re.sub(r"[-_.\s]", "", (nombre or "").upper())


def detectar_duplicados(session) -> list[dict]:
    """Detecta grupos con la misma normalización (más de un id).

    El canónico es el registro cuyo nombre NO tiene guiones (el del catálogo
    original con precios). El duplicado es el que tiene guiones (creado por
    el importador desde el CSV legacy).
    """
    disenos = session.query(DisenoLlanta).all()
    por_norm: dict[str, list[DisenoLlanta]] = {}
    for d in disenos:
        por_norm.setdefault(normalizar(d.nombre), []).append(d)

    duplicados = []
    for norm, grupo in por_norm.items():
        if len(grupo) > 1:
            # Canónico = nombre sin guiones; duplicado = con guiones
            canonicos = [d for d in grupo if "-" not in d.nombre]
            duplicados_list = [d for d in grupo if "-" in d.nombre]
            if not canonicos or not duplicados_list:
                # Caso raro: todos con/sin guion — fallback por precios/llantas/id
                grupo.sort(key=lambda d: (
                    -session.query(PrecioProducto).filter(PrecioProducto.diseno_id == d.id).count(),
                    -session.query(Llanta).filter(Llanta.diseno_id == d.id).count(),
                    d.id,
                ))
                canonico = grupo[0]
                duplicados_list = grupo[1:]
            else:
                canonico = canonicos[0]
                duplicados_list = duplicados_list

            for dup in duplicados_list:
                n_llantas = session.query(Llanta).filter(Llanta.diseno_id == dup.id).count()
                n_precios = session.query(PrecioProducto).filter(PrecioProducto.diseno_id == dup.id).count()
                duplicados.append({
                    "norm": norm,
                    "canonico": canonico,
                    "duplicado": dup,
                    "llantas": n_llantas,
                    "precios": n_precios,
                })
    return duplicados


def aplicar(session, ejecutar: bool) -> dict:
    duplicados = detectar_duplicados(session)
    print(f"Diseños duplicados detectados: {len(duplicados)}")

    total_llantas = sum(d["llantas"] for d in duplicados)
    total_precios = sum(d["precios"] for d in duplicados)

    for d in duplicados:
        print(f"  {d['duplicado'].nombre} (id={d['duplicado'].id}) -> "
              f"{d['canonico'].nombre} (id={d['canonico'].id}) | "
              f"{d['llantas']} llantas, {d['precios']} precios")

    if not ejecutar:
        print(f"\n>>> MODO SIMULACION: total {total_llantas} llantas, "
              f"{total_precios} precios a reasignar.")
        return {"modo": "dry-run", "duplicados": len(duplicados),
                "llantas": total_llantas, "precios": total_precios}

    # ── MODO REAL ──
    from src.core.services.backup_service import create_backup
    ok_bk, msg_bk = create_backup()
    if not ok_bk:
        print(f"[ERROR] No se pudo crear el respaldo: {msg_bk}")
        sys.exit(1)
    print(f"[BACKUP] {msg_bk}")

    for d in duplicados:
        dup_id = d["duplicado"].id
        can_id = d["canonico"].id

        # Reasignar llantas
        n_ll = session.query(Llanta).filter(Llanta.diseno_id == dup_id).update(
            {Llanta.diseno_id: can_id}
        )
        # Reasignar precios (si el duplicado tuviera)
        n_pr = session.query(PrecioProducto).filter(
            PrecioProducto.diseno_id == dup_id
        ).update({PrecioProducto.diseno_id: can_id})
        # Eliminar duplicado
        session.delete(d["duplicado"])
        print(f"  [{d['duplicado'].nombre} -> {d['canonico'].nombre}] "
              f"llantas={n_ll}, precios={n_pr}, eliminado")

    session.commit()
    return {"modo": "real", "duplicados": len(duplicados),
            "llantas": total_llantas, "precios": total_precios}


def main() -> None:
    parser = argparse.ArgumentParser(description="Unificar diseños duplicados por normalización")
    parser.add_argument("--ejecutar", action="store_true",
                        help="Aplica la unificación con backup (por defecto solo simula)")
    args = parser.parse_args()

    print(f"Base de datos: {DB_PATH}\n")
    with get_session() as session:
        resumen = aplicar(session, ejecutar=args.ejecutar)

    if resumen["modo"] == "real":
        print(f"\n[RESULTADO] {resumen['duplicados']} duplicados unificados, "
              f"{resumen['llantas']} llantas reasignadas, "
              f"{resumen['precios']} precios reasignados")
    print("\n[OK] Unificación completada.")


if __name__ == "__main__":
    main()