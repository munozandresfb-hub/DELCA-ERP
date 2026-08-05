from datetime import datetime
from decimal import Decimal

from src.database.engine import get_session
from src.modules.inventario.models.movimiento_inventario_model import (
    MovimientoInventario,
)
from src.modules.inventario.models.producto_model import Producto


class ProductoService:
    """Business logic for product/inventory management."""

    CATEGORIAS = [
        "MATERIA_PRIMA",
        "INSUMOS",
        "HERRAMIENTAS",
        "REPUESTOS",
        "EMPAQUES",
        "OTROS",
    ]

    @staticmethod
    def listar_productos(
        categoria: str | None = None, solo_activos: bool = False
    ) -> list[Producto]:
        with get_session() as session:
            q = session.query(Producto)
            if categoria:
                q = q.filter(Producto.categoria == categoria)
            if solo_activos:
                q = q.filter(Producto.activo.is_(True))
            productos = q.order_by(Producto.nombre).all()
            for p in productos:
                session.expunge(p)
            return productos

    @staticmethod
    def buscar(termino: str) -> list[Producto]:
        with get_session() as session:
            pattern = f"%{termino}%"
            productos = (
                session.query(Producto)
                .filter(
                    Producto.nombre.ilike(pattern)
                    | Producto.sku.ilike(pattern)
                    | Producto.categoria.ilike(pattern)
                )
                .order_by(Producto.nombre)
                .all()
            )
            for p in productos:
                session.expunge(p)
            return productos

    @staticmethod
    def obtener_por_id(producto_id: int) -> Producto | None:
        with get_session() as session:
            producto = (
                session.query(Producto)
                .filter(Producto.id == producto_id)
                .first()
            )
            if producto:
                session.expunge(producto)
            return producto

    @staticmethod
    def crear(
        nombre: str,
        sku: str,
        descripcion: str | None = None,
        categoria: str | None = None,
        costo_unitario: Decimal = Decimal("0"),
        precio_venta: Decimal = Decimal("0"),
        stock_inicial: Decimal = Decimal("0"),
        stock_minimo: Decimal = Decimal("0"),
        unidad_medida: str = "UNIDAD",
    ) -> tuple[bool, str | Producto]:
        if not nombre or not nombre.strip():
            return False, "El nombre es obligatorio"
        if not sku or not sku.strip():
            return False, "El SKU es obligatorio"

        with get_session() as session:
            existente_sku = (
                session.query(Producto)
                .filter(Producto.sku == sku.strip())
                .first()
            )
            if existente_sku:
                return False, f"Ya existe un producto con SKU {sku}"
            existente_nombre = (
                session.query(Producto)
                .filter(Producto.nombre == nombre.strip())
                .first()
            )
            if existente_nombre:
                return False, f"Ya existe un producto con el nombre '{nombre.strip()}'"

            producto = Producto(
                nombre=nombre.strip(),
                sku=sku.strip().upper(),
                descripcion=descripcion.strip()
                if descripcion
                else None,
                categoria=categoria,
                stock=stock_inicial,
                stock_minimo=stock_minimo,
                costo_unitario=costo_unitario,
                precio_venta=precio_venta,
                unidad_medida=unidad_medida.upper(),
                activo=True,
            )
            session.add(producto)
            session.flush()

            # Register initial stock as an entry movement
            if stock_inicial > 0:
                mov = MovimientoInventario(
                    producto_id=producto.id,
                    tipo="ENTRADA",
                    cantidad=stock_inicial,
                    costo_unitario=costo_unitario,
                    referencia="INVENTARIO_INICIAL",
                    observaciones="Stock inicial",
                )
                session.add(mov)

            session.expunge(producto)
            return True, producto

    @staticmethod
    def actualizar(
        producto_id: int,
        nombre: str,
        sku: str,
        descripcion: str | None = None,
        categoria: str | None = None,
        costo_unitario: Decimal = Decimal("0"),
        precio_venta: Decimal = Decimal("0"),
        unidad_medida: str = "UNIDAD",
        activo: bool = True,
    ) -> tuple[bool, str]:
        with get_session() as session:
            producto = (
                session.query(Producto)
                .filter(Producto.id == producto_id)
                .first()
            )
            if not producto:
                return False, "Producto no encontrado"

            # Check SKU uniqueness
            if sku.strip().upper() != producto.sku:
                existente = (
                    session.query(Producto)
                    .filter(Producto.sku == sku.strip().upper())
                    .first()
                )
                if existente:
                    return False, f"Ya existe otro producto con SKU {sku}"

            producto.nombre = nombre.strip()
            producto.sku = sku.strip().upper()
            producto.descripcion = descripcion.strip() if descripcion else None
            producto.categoria = categoria
            producto.costo_unitario = costo_unitario
            producto.precio_venta = precio_venta
            producto.unidad_medida = unidad_medida.upper()
            producto.activo = activo

            return True, "Producto actualizado"

    @staticmethod
    def eliminar(producto_id: int) -> tuple[bool, str]:
        with get_session() as session:
            producto = (
                session.query(Producto)
                .filter(Producto.id == producto_id)
                .first()
            )
            if not producto:
                return False, "Producto no encontrado"
            session.delete(producto)
            return True, "Producto eliminado"

    @staticmethod
    def registrar_movimiento(
        producto_id: int,
        tipo: str,
        cantidad: Decimal,
        costo_unitario: Decimal | None = None,
        referencia: str | None = None,
        observaciones: str | None = None,
        usuario_id: int | None = None,
        documento_id: int | None = None,
    ) -> tuple[bool, str]:
        if tipo not in ("ENTRADA", "SALIDA", "MERMA", "AJUSTE"):
            return False, f"Tipo inválido: {tipo}"
        if cantidad < 0:
            return False, "La cantidad no puede ser negativa"
        if cantidad == 0 and tipo != "AJUSTE":
            return False, "La cantidad debe ser mayor a cero"

        with get_session() as session:
            producto = (
                session.query(Producto)
                .filter(Producto.id == producto_id)
                .first()
            )
            if not producto:
                return False, "Producto no encontrado"

            # Validate stock for SALIDA
            if tipo in ("SALIDA", "MERMA") and cantidad > producto.stock:
                return (
                    False,
                    f"Stock insuficiente: {producto.stock}",
                )

            # Update stock
            if tipo == "ENTRADA":
                producto.stock += cantidad
            elif tipo == "SALIDA":
                producto.stock -= cantidad
            elif tipo == "MERMA":
                producto.stock -= cantidad
            elif tipo == "AJUSTE":
                producto.stock = cantidad  # absolute set

            costo = costo_unitario or producto.costo_unitario

            mov = MovimientoInventario(
                producto_id=producto_id,
                tipo=tipo,
                cantidad=cantidad,
                costo_unitario=costo,
                referencia=referencia.strip() if referencia else None,
                observaciones=observaciones.strip()
                if observaciones
                else None,
                usuario_id=usuario_id,
                documento_id=documento_id,
            )
            session.add(mov)

            return True, f"{tipo} registrada. Stock: {producto.stock}"

    @staticmethod
    def obtener_kardex(
        producto_id: int, limite: int = 50
    ) -> list[MovimientoInventario]:
        with get_session() as session:
            return (
                session.query(MovimientoInventario)
                .filter(MovimientoInventario.producto_id == producto_id)
                .order_by(MovimientoInventario.fecha.desc())
                .limit(limite)
                .all()
            )

    @staticmethod
    def obtener_kardex_por_filtros(
        producto_id: int | None = None,
        tipo: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        limite: int = 500,
    ) -> list[MovimientoInventario]:
        """Query movements with optional filters and ASC ordering (for balance calc)."""
        with get_session() as session:
            q = session.query(MovimientoInventario)
            if producto_id:
                q = q.filter(MovimientoInventario.producto_id == producto_id)
            if tipo and tipo != "Todos":
                q = q.filter(MovimientoInventario.tipo == tipo)
            if fecha_desde:
                q = q.filter(MovimientoInventario.fecha >= fecha_desde)
            if fecha_hasta:
                q = q.filter(MovimientoInventario.fecha <= fecha_hasta)
            results = q.order_by(MovimientoInventario.fecha.asc()).limit(limite).all()
            for r in results:
                session.expunge(r)
            return results

    @staticmethod
    def obtener_resumen_stock() -> list[tuple[str, str]]:
        """Get stock summary across all products."""
        with get_session() as session:
            productos = (
                session.query(Producto)
                .order_by(Producto.nombre)
                .all()
            )
            total_productos = len(productos)
            total_stock = sum(p.stock for p in productos if p.stock)
            valor_total = sum(
                p.stock * p.costo_unitario
                for p in productos
                if p.stock and p.costo_unitario
            )

            # Count products with low stock
            bajos = sum(1 for p in productos if 0 < p.stock < 10)

            return [
                ("Total Productos", str(total_productos)),
                ("Total Unidades", str(total_stock)),
                ("Valor Inventario", f"${valor_total:,.2f}"),
                ("Stock Bajo", str(bajos)),
            ]

    @staticmethod
    def listar_categorias() -> list[str]:
        with get_session() as session:
            resultados = (
                session.query(Producto.categoria)
                .filter(Producto.categoria.isnot(None))
                .distinct()
                .order_by(Producto.categoria)
                .all()
            )
            return [r[0] for r in resultados]
