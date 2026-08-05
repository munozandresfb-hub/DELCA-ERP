from decimal import Decimal

from src.database.engine import get_session
from src.modules.inventario.models.inventario_config_models import (
    CostoProduccionEstandar,
    PrecioVentaCliente,
    RecetaProduccion,
)


class InventarioConfigService:
    """Unified CRUD for inventory configuration tables."""

    # ── Costo Produccion Estandar ────────────────────────────────────

    @staticmethod
    def listar_costos(
        diseno_id: int | None = None, dimension_id: int | None = None
    ) -> list[CostoProduccionEstandar]:
        with get_session() as session:
            q = session.query(CostoProduccionEstandar)
            if diseno_id:
                q = q.filter(CostoProduccionEstandar.diseno_id == diseno_id)
            if dimension_id:
                q = q.filter(CostoProduccionEstandar.dimension_id == dimension_id)
            resultados = q.order_by(CostoProduccionEstandar.diseno_id).all()
            for r in resultados:
                session.expunge(r)
            return resultados

    @staticmethod
    def obtener_costo(
        diseno_id: int, dimension_id: int
    ) -> CostoProduccionEstandar | None:
        with get_session() as session:
            r = (
                session.query(CostoProduccionEstandar)
                .filter(
                    CostoProduccionEstandar.diseno_id == diseno_id,
                    CostoProduccionEstandar.dimension_id == dimension_id,
                )
                .first()
            )
            if r:
                session.expunge(r)
            return r

    @staticmethod
    def guardar_costo(
        diseno_id: int, dimension_id: int, costo: Decimal
    ) -> tuple[bool, str]:
        with get_session() as session:
            existente = (
                session.query(CostoProduccionEstandar)
                .filter(
                    CostoProduccionEstandar.diseno_id == diseno_id,
                    CostoProduccionEstandar.dimension_id == dimension_id,
                )
                .first()
            )
            if existente:
                existente.costo_produccion = costo
            else:
                nuevo = CostoProduccionEstandar(
                    diseno_id=diseno_id, dimension_id=dimension_id, costo_produccion=costo
                )
                session.add(nuevo)
            return True, "Costo guardado"

    @staticmethod
    def eliminar_costo(costo_id: int) -> tuple[bool, str]:
        with get_session() as session:
            r = (
                session.query(CostoProduccionEstandar)
                .filter(CostoProduccionEstandar.id == costo_id)
                .first()
            )
            if not r:
                return False, "Costo no encontrado"
            session.delete(r)
            return True, "Costo eliminado"

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
    def obtener_precio(
        cliente_id: int, diseno_id: int, dimension_id: int
    ) -> PrecioVentaCliente | None:
        with get_session() as session:
            r = (
                session.query(PrecioVentaCliente)
                .filter(
                    PrecioVentaCliente.cliente_id == cliente_id,
                    PrecioVentaCliente.diseno_id == diseno_id,
                    PrecioVentaCliente.dimension_id == dimension_id,
                )
                .first()
            )
            if r:
                session.expunge(r)
            return r

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

    # ── Receta Produccion ────────────────────────────────────────────

    @staticmethod
    def listar_recetas(
        diseno_id: int | None = None,
        dimension_id: int | None = None,
        producto_id: int | None = None,
    ) -> list[RecetaProduccion]:
        with get_session() as session:
            q = session.query(RecetaProduccion)
            if diseno_id:
                q = q.filter(RecetaProduccion.diseno_id == diseno_id)
            if dimension_id:
                q = q.filter(RecetaProduccion.dimension_id == dimension_id)
            if producto_id:
                q = q.filter(RecetaProduccion.producto_id == producto_id)
            resultados = q.order_by(RecetaProduccion.diseno_id).all()
            for r in resultados:
                session.expunge(r)
            return resultados

    @staticmethod
    def guardar_receta(
        diseno_id: int,
        dimension_id: int,
        producto_id: int,
        cantidad: Decimal,
        unidad: str = "UNIDAD",
    ) -> tuple[bool, str]:
        with get_session() as session:
            existente = (
                session.query(RecetaProduccion)
                .filter(
                    RecetaProduccion.diseno_id == diseno_id,
                    RecetaProduccion.dimension_id == dimension_id,
                    RecetaProduccion.producto_id == producto_id,
                )
                .first()
            )
            if existente:
                existente.cantidad = cantidad
                existente.unidad = unidad
            else:
                nuevo = RecetaProduccion(
                    diseno_id=diseno_id,
                    dimension_id=dimension_id,
                    producto_id=producto_id,
                    cantidad=cantidad,
                    unidad=unidad,
                )
                session.add(nuevo)
            return True, "Receta guardada"

    @staticmethod
    def eliminar_receta(receta_id: int) -> tuple[bool, str]:
        with get_session() as session:
            r = (
                session.query(RecetaProduccion)
                .filter(RecetaProduccion.id == receta_id)
                .first()
            )
            if not r:
                return False, "Receta no encontrada"
            session.delete(r)
            return True, "Receta eliminada"
