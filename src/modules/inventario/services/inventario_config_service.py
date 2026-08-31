from decimal import Decimal

from src.database.engine import get_session
from src.modules.inventario.models.inventario_config_models import (
    PrecioVentaCliente,
)


class InventarioConfigService:
    """CRUD para precios de venta por cliente (tablas de configuración)."""

    # ── Precio Venta Cliente ────────────────────────────────────────

    @staticmethod
    def listar_precios(
        cliente_id: int | None = None,
        diseno_id: int | None = None,
        dimension_id: int | None = None,
    ) -> list[PrecioVentaCliente]:
        with get_session() as session:
            q = session.query(PrecioVentaCliente)
            if cliente_id:
                q = q.filter(PrecioVentaCliente.cliente_id == cliente_id)
            if diseno_id:
                q = q.filter(PrecioVentaCliente.diseno_id == diseno_id)
            if dimension_id:
                q = q.filter(PrecioVentaCliente.dimension_id == dimension_id)
            resultados = q.order_by(PrecioVentaCliente.cliente_id).all()
            for r in resultados:
                session.expunge(r)
            return resultados

    @staticmethod
    def guardar_precio(
        cliente_id: int,
        diseno_id: int,
        dimension_id: int,
        precio: Decimal,
    ) -> tuple[bool, str]:
        with get_session() as session:
            existente = (
                session.query(PrecioVentaCliente)
                .filter(
                    PrecioVentaCliente.cliente_id == cliente_id,
                    PrecioVentaCliente.diseno_id == diseno_id,
                    PrecioVentaCliente.dimension_id == dimension_id,
                )
                .first()
            )
            if existente:
                existente.precio_venta = precio
            else:
                nuevo = PrecioVentaCliente(
                    cliente_id=cliente_id,
                    diseno_id=diseno_id,
                    dimension_id=dimension_id,
                    precio_venta=precio,
                )
                session.add(nuevo)
            return True, "Precio guardado"

    @staticmethod
    def eliminar_precio(precio_id: int) -> tuple[bool, str]:
        with get_session() as session:
            r = (
                session.query(PrecioVentaCliente)
                .filter(PrecioVentaCliente.id == precio_id)
                .first()
            )
            if not r:
                return False, "Precio no encontrado"
            session.delete(r)
            return True, "Precio eliminado"