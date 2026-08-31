"""
Aplicador de precios desde precios_producto a las llantas terminadas.

Copia 'precio_normal' de precios_producto → llantas.precio_venta para las
llantas REENCAUCHADA/REPARADA que tengan dimension_id + diseno_id con
cobertura en la lista de precios. SOLO si precio_venta está vacío
(no pisa precios ya asignados).

Las llantas sin cobertura (combinación dimension+diseno ausente en
precios_producto) quedan sin precio y se registran en un reporte CSV.

Modos:
    python scripts/aplicar_precios.py             # DRY-RUN: simula
    python scripts/aplicar_precios.py --ejecutar  # REAL: backup + carga
"""

import argparse
import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import src.database.registry  # noqa: F401

from src.database.engine import DB_PATH, get_session  # noqa: E402

from src.modules.llantas.models.llanta_model import Llanta  # noqa: E402
from src.modules.inventario.models.precio_producto_model import PrecioProducto  # noqa: E402

REPORTE_FALTANTES = Path(
    r"C:\Users\andre\OneDrive\Escritorio\DELCA\precios faltantes.csv"
)


def aplicar(session, ejecutar: bool) -> dict:
    """Aplica precios a llantas terminadas. Devuelve conteos."""
    # Índice de precios: (dimension_id, diseno_id) -> precio_normal
    precios = {}
    for p in session.query(PrecioProducto).all():
        if p.dimension_id and p.diseno_id:
            precios[(p.dimension_id, p.diseno_id)] = p.precio_normal

    # Llantas terminadas elegibles
    terminadas = session.query(Llanta).filter(
        Llanta.estado.in_(["REENCAUCHADA", "REPARADA"]),
    ).all()

    cubiertas = 0
    sin_cubrir = 0
    sin_dim_dis = 0
    ya_tienen = 0
    por_aplicar = []
    faltantes = []

    for l in terminadas:
        if not l.dimension_id or not l.diseno_id:
            sin_dim_dis += 1
            continue
        if l.precio_venta is not None and l.precio_venta > 0:
            ya_tienen += 1
            continue
        precio = precios.get((l.dimension_id, l.diseno_id))
        if precio is None:
            sin_cubrir += 1
            faltantes.append((l.tiquete, l.dimension, l.estado, l.ubicacion_actual))
            continue
        cubiertas += 1
        por_aplicar.append((l, float(precio)))

    # ── Reporte de faltantes (siempre se genera) ──
    with open(REPORTE_FALTANTES, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tiquete", "dimension", "estado", "ubicacion_actual"])
        w.writerows(faltantes)

    print(f"  Terminadas (REENCAUCHADA+REPARADA): {len(terminadas)}")
    print(f"  Con precio aplicable (precio_normal): {cubiertas}")
    print(f"  Ya tenían precio (no se tocan): {ya_tienen}")
    print(f"  Sin cobertura en precios_producto: {sin_cubrir}")
    print(f"  Sin dimension_id o diseno_id: {sin_dim_dis}")
    print(f"  Reporte de faltantes: {REPORTE_FALTANTES.name} ({len(faltantes)} filas)")

    if not ejecutar:
        print("\n>>> MODO SIMULACION: no se escribe en la BD.")
        return {"modo": "dry-run", "aplicar": len(por_aplicar),
                "sin_cubrir": sin_cubrir, "sin_dim_dis": sin_dim_dis}

    # ── MODO REAL ──
    from src.core.services.backup_service import create_backup
    ok_bk, msg_bk = create_backup()
    if not ok_bk:
        print(f"[ERROR] No se pudo crear el respaldo: {msg_bk}")
        sys.exit(1)
    print(f"[BACKUP] {msg_bk}")

    for l, precio in por_aplicar:
        l.precio_venta = precio
    session.commit()

    return {"modo": "real", "aplicados": len(por_aplicar),
            "sin_cubrir": sin_cubrir, "sin_dim_dis": sin_dim_dis}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aplicar precios de precios_producto a llantas terminadas"
    )
    parser.add_argument("--ejecutar", action="store_true",
                        help="Carga real con respaldo previo (por defecto solo simula)")
    args = parser.parse_args()

    print(f"Base de datos: {DB_PATH}\n")
    with get_session() as session:
        resumen = aplicar(session, ejecutar=args.ejecutar)

    if resumen["modo"] == "real":
        print(f"\n[RESULTADO] Precios aplicados: {resumen['aplicados']}")
    print("\n[OK] Aplicación de precios completada.")


if __name__ == "__main__":
    main()