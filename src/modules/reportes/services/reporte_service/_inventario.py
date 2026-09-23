"""Reportes de Inventario."""

from sqlalchemy import case, func

from src.database.engine import get_session
from src.modules.inventario.models.movimiento_inventario_model import (
    MovimientoInventario,
)
from src.modules.inventario.models.producto_model import Producto


class _InventarioReports:
    """Reportes del dominio Inventario."""

    @staticmethod
    def inventario_por_categoria() -> list[dict]:
        """Per-product inventory with category, name, code, stock, value.

        Para bandas (unidad ROLLO/ROLLOS) el costo es por KG → valor =
        stock_kg × costo. Para el resto de unidades el costo es por unidad.
        """
        with get_session() as session:
            valor_expr = (
                case(
                    (
                        func.upper(Producto.unidad_medida).in_(["ROLLO", "ROLLOS"]),
                        Producto.stock_kg,
                    ),
                    else_=Producto.stock,
                )
                * Producto.costo_unitario
            )
            results = (
                session.query(
                    Producto.categoria,
                    Producto.nombre,
                    Producto.sku,
                    Producto.stock,
                    Producto.stock_kg,
                    valor_expr,
                )
                .filter(Producto.activo.is_(True))
                .order_by(Producto.categoria, Producto.nombre)
                .all()
            )
            return [
                {
                    "categoria": r[0] or "SIN CATEGORIA",
                    "producto": r[1],
                    "codigo": r[2] or "",
                    "stock": float(r[3] or 0),
                    "stock_kg": float(r[4] or 0),
                    "valor": float(r[5] or 0),
                }
                for r in results
            ]

    @staticmethod
    def movimientos_por_tipo() -> list[dict]:
        """Movements with consecutive row number for each report."""
        with get_session() as session:
            results = (
                session.query(
                    MovimientoInventario.tipo,
                    func.count(MovimientoInventario.id),
                    func.sum(MovimientoInventario.cantidad),
                )
                .group_by(MovimientoInventario.tipo)
                .order_by(MovimientoInventario.tipo)
                .all()
            )
            return [
                {
                    "consecutivo": i + 1,
                    "tipo": r[0] or "OTRO",
                    "cantidad": r[1],
                    "total_unidades": float(r[2] or 0),
                }
                for i, r in enumerate(results)
            ]

    @staticmethod
    def productos_stock_bajo(limite: int = 10) -> list[dict]:
        with get_session() as session:
            productos = (
                session.query(Producto)
                .filter(
                    Producto.activo.is_(True),
                    Producto.stock < 10,
                )
                .order_by(Producto.stock.asc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "nombre": p.nombre,
                    "sku": p.sku,
                    "stock": float(p.stock or 0),
                }
                for p in productos
            ]