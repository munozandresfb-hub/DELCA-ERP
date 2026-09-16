"""Costo y precio de referencia de llantas desde el catálogo de precios.

Regla de negocio (2026-09-15, indicación del cliente):
  - COSTO  = catálogo.precios_producto.costo_fabricacion por (diseño + dimensión).
    Sin cobertura en el catálogo → se usa el costo_produccion propio de la llanta.
  - PRECIO = precio de venta del catálogo (precio_normal) por (diseño + dimensión).
    Si la referencia no tiene precio_normal asignado → se usa precio_minimo.
    Si la llanta NO tiene cobertura en el catálogo → precio de referencia = 1 peso
    (marca el mínimo posible; evita utilidad/margen con precio 0 o división por cero).
"""
from __future__ import annotations

from src.modules.inventario.models.precio_producto_model import PrecioProducto

PRECIO_SIN_COBERTURA = 1.0  # 1 peso para llantas sin cobertura en el catálogo


def indice_precios(session) -> dict[tuple[int, int], dict]:
    """Construye el índice del catálogo: (dimension_id, diseno_id) → precios.

    Cada entrada: {"costo": costo_fabricacion, "precio_venta": precio_normal,
                   "precio_minimo": precio_minimo}
    """
    idx: dict[tuple[int, int], dict] = {}
    for p in session.query(PrecioProducto).all():
        if p.dimension_id and p.diseno_id:
            idx[(p.dimension_id, p.diseno_id)] = {
                "costo": float(p.costo_fabricacion or 0),
                "precio_venta": float(p.precio_normal or 0),
                "precio_minimo": float(p.precio_minimo or 0),
            }
    return idx


def costo_precio(llanta, indice: dict) -> tuple[float, float]:
    """Resuelve (costo, precio) de una llanta según el catálogo (ver docstring del módulo)."""
    dim = getattr(llanta, "dimension_id", None)
    dis = getattr(llanta, "diseno_id", None)
    reg = indice.get((dim, dis)) if (dim and dis) else None

    if reg:
        costo = reg["costo"] if reg["costo"] > 0 else float(getattr(llanta, "costo_produccion", 0) or 0)
        precio = reg["precio_venta"] if reg["precio_venta"] > 0 else reg["precio_minimo"]
        if precio <= 0:
            precio = PRECIO_SIN_COBERTURA
    else:
        costo = float(getattr(llanta, "costo_produccion", 0) or 0)
        precio = PRECIO_SIN_COBERTURA  # sin cobertura en el catálogo → 1 peso
    return costo, precio