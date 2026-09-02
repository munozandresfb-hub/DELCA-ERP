"""Resumen general para el dashboard de reportes."""

from datetime import datetime

from sqlalchemy import func

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.finanzas.models.pago_model import Pago
from src.modules.inventario.models.movimiento_inventario_model import (
    MovimientoInventario,
)
from src.modules.inventario.models.producto_model import Producto
from src.core.services.cliente_actividad import contar_clientes_activos_inactivos
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.services.llanta_service import ESTADOS_EN_PLANTA


class _DashboardReports:
    """Resumen global para el dashboard."""

    @staticmethod
    def obtener_resumen_completo() -> dict:
        """Get a complete summary for the dashboard report."""
        with get_session() as session:
            total_clientes = session.query(Cliente).count()
            # Clientes activos/inactivos con la DEFINICIÓN CENTRAL (actividad
            # completa), coherente con el dashboard principal y el reporte de clientes.
            clientes_activos, clientes_inactivos = contar_clientes_activos_inactivos()
            llantas_planta = session.query(Llanta).filter(
                Llanta.estado.in_(ESTADOS_EN_PLANTA),
                (Llanta.ubicacion_actual.is_(None))
                | (Llanta.ubicacion_actual != "CLIENTE"),
            ).count()
            total_llantas = session.query(Llanta).count()
            total_facturas = session.query(Factura).count()
            facturas_pendientes = session.query(Factura).filter(Factura.saldo > 0).count()
            total_productos = (
                session.query(Producto)
                .filter(Producto.activo.is_(True))
                .count()
            )
            productos_stock_bajo = session.query(Producto).filter(
                Producto.activo.is_(True), Producto.stock < 10,
            ).count()
            total_pagos = session.query(Pago).count()
            total_movs = (
                session.query(MovimientoInventario).count()
            )

            facturacion_total = (
                session.query(
                    func.coalesce(func.sum(Factura.total), 0)
                )
                .filter(
                    func.strftime("%Y", Factura.fecha_emision)
                    == str(datetime.now().year)
                )
                .scalar()
            )

            valor_inventario = (
                session.query(
                    func.coalesce(
                        func.sum(
                            Producto.stock * Producto.costo_unitario
                        ),
                        0,
                    )
                )
                .filter(Producto.activo.is_(True))
                .scalar()
            )

        return {
            "total_clientes": total_clientes,
            "clientes_activos": clientes_activos,
            "clientes_inactivos": clientes_inactivos,
            "total_llantas": total_llantas,
            "llantas_en_planta": llantas_planta,
            "total_facturas": total_facturas,
            "facturas_pendientes": facturas_pendientes,
            "total_productos": total_productos,
            "productos_stock_bajo": productos_stock_bajo,
            "total_pagos": total_pagos,
            "total_movimientos": total_movs,
            "facturacion_anual": float(facturacion_total),
            "valor_inventario": float(valor_inventario),
        }