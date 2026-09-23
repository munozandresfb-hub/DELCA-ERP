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
        "CONSUMIBLE",
        "INSUMOS",
        "HERRAMIENTAS",
        "REPUESTOS",
        "EMPAQUES",
        "OTROS",
    ]

    # Unidades que se valoran por KG (bandas de rodadura, etc.)
    UNIDADES_POR_KG = {"ROLLO", "ROLLOS"}

    @staticmethod
    def valor_inventario_producto(producto: Producto) -> float:
        """Valor monetario de un producto en inventario.

        Para unidades por KG (ROLLO/ROLLOS, ej. bandas de rodadura) el costo
        unitario está expresado en COP/KG, por lo que el valor es
        ``stock_kg × costo_unitario``. Para el resto de unidades
        (UNIDAD, CAJA, PAQ...) el costo es por unidad y el valor es
        ``stock × costo_unitario``.
        """
        unidad = str(getattr(producto, "unidad_medida", "") or "").upper()
        if unidad in ProductoService.UNIDADES_POR_KG:
            return float(producto.stock_kg or 0) * float(
                producto.costo_unitario or 0
            )
        return float(producto.stock or 0) * float(producto.costo_unitario or 0)

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
        stock_kg: Decimal = Decimal("0"),
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
                stock_kg=stock_kg,
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
    def crear_documento(
        numero_documento: str,
        tipo: str,
        fecha=None,
        observaciones: str | None = None,
    ) -> tuple[bool, str | int]:
        """Crea un documento de inventario (INGRESO con factura / SALIDA con consecutivo)."""
        from datetime import date

        from src.modules.inventario.models.documento_model import DocumentoInventario

        if not numero_documento or not numero_documento.strip():
            return False, "El número del documento es obligatorio"
        if tipo not in ("INGRESO", "SALIDA"):
            return False, f"Tipo de documento inválido: {tipo}"
        numero = numero_documento.strip()
        with get_session() as session:
            existe = (
                session.query(DocumentoInventario)
                .filter(DocumentoInventario.numero_documento == numero)
                .first()
            )
            if existe:
                # Un documento puede agrupar varios productos: se REUTILIZA
                return True, existe.id
            doc = DocumentoInventario(
                numero_documento=numero,
                tipo=tipo,
                fecha=fecha or date.today(),
                observaciones=observaciones,
            )
            session.add(doc)
            session.flush()
            return True, doc.id

    @staticmethod
    def listar_documentos() -> list:
        """Lista los documentos de inventario (más recientes primero)."""
        from src.modules.inventario.models.documento_model import DocumentoInventario

        with get_session() as session:
            docs = (
                session.query(DocumentoInventario)
                .order_by(DocumentoInventario.fecha.desc(), DocumentoInventario.id.desc())
                .all()
            )
            for d in docs:
                session.expunge(d)
            return docs

    @staticmethod
    def movimientos_por_documento(documento_id: int) -> list[dict]:
        """Movimientos de un documento con la información del producto."""
        from src.modules.inventario.models.movimiento_inventario_model import (
            MovimientoInventario,
        )

        with get_session() as session:
            rows = (
                session.query(MovimientoInventario, Producto)
                .join(Producto, MovimientoInventario.producto_id == Producto.id)
                .filter(MovimientoInventario.documento_id == documento_id)
                .order_by(MovimientoInventario.fecha)
                .all()
            )
            return [
                {
                    "id": m.id,
                    "producto": p.nombre,
                    "sku": p.sku,
                    "unidad": p.unidad_medida or "",
                    "tipo": m.tipo or "",
                    "cantidad": m.cantidad,
                    "cantidad_kg": m.cantidad_kg or 0,
                    "fecha": m.fecha,
                    "referencia": m.referencia or "",
                    "observaciones": m.observaciones or "",
                }
                for m, p in rows
            ]

    @staticmethod
    def editar_movimiento(
        movimiento_id: int,
        cantidad: Decimal,
        cantidad_kg: Decimal = Decimal("0"),
        fecha=None,
        observaciones: str | None = None,
    ) -> tuple[bool, str]:
        """Edita un movimiento de inventario ajustando el stock del producto.

        ENTRADA/SALIDA: revierte el efecto original y aplica el nuevo.
        AJUSTE: fija el stock al nuevo valor indicado.
        """
        from src.modules.inventario.models.movimiento_inventario_model import (
            MovimientoInventario,
        )

        with get_session() as session:
            mov = (
                session.query(MovimientoInventario)
                .filter(MovimientoInventario.id == movimiento_id)
                .first()
            )
            if not mov:
                return False, "Movimiento no encontrado"
            producto = session.query(Producto).filter(Producto.id == mov.producto_id).first()
            if not producto:
                return False, "Producto no encontrado"
            if cantidad < 0 or cantidad_kg < 0:
                return False, "Las cantidades no pueden ser negativas"

            # Revertir el efecto original
            if mov.tipo == "ENTRADA":
                producto.stock -= mov.cantidad
                producto.stock_kg -= Decimal(mov.cantidad_kg or 0)
            elif mov.tipo in ("SALIDA", "MERMA"):
                producto.stock += mov.cantidad
                producto.stock_kg += Decimal(mov.cantidad_kg or 0)

            # Validar stock suficiente para la nueva salida
            if mov.tipo in ("SALIDA", "MERMA") and cantidad > producto.stock:
                return False, f"Stock insuficiente: {producto.stock}"
            if mov.tipo in ("SALIDA", "MERMA") and cantidad_kg > producto.stock_kg:
                return False, f"Stock insuficiente en KG: {producto.stock_kg}"

            # Aplicar el nuevo valor
            if mov.tipo == "ENTRADA":
                producto.stock += cantidad
                producto.stock_kg += cantidad_kg
            elif mov.tipo in ("SALIDA", "MERMA"):
                producto.stock -= cantidad
                producto.stock_kg -= cantidad_kg
            elif mov.tipo == "AJUSTE":
                producto.stock = cantidad
                producto.stock_kg = cantidad_kg

            mov.cantidad = cantidad
            mov.cantidad_kg = cantidad_kg
            if fecha is not None:
                mov.fecha = fecha
            if observaciones is not None:
                mov.observaciones = observaciones.strip() or None
            return True, f"Movimiento actualizado. Stock: {producto.stock}"

    @staticmethod
    def eliminar_movimiento(movimiento_id: int) -> tuple[bool, str]:
        """Elimina un movimiento de inventario y revierte su efecto en el stock.

        Un AJUSTE no se puede eliminar (el stock quedó fijado por el ajuste).
        """
        from src.modules.inventario.models.movimiento_inventario_model import (
            MovimientoInventario,
        )

        with get_session() as session:
            mov = (
                session.query(MovimientoInventario)
                .filter(MovimientoInventario.id == movimiento_id)
                .first()
            )
            if not mov:
                return False, "Movimiento no encontrado"
            if mov.tipo == "AJUSTE":
                return False, "No se puede eliminar un ajuste (el stock quedó fijado)"
            producto = session.query(Producto).filter(Producto.id == mov.producto_id).first()
            if mov.tipo == "ENTRADA":
                producto.stock -= mov.cantidad
                producto.stock_kg -= Decimal(mov.cantidad_kg or 0)
            elif mov.tipo in ("SALIDA", "MERMA"):
                producto.stock += mov.cantidad
                producto.stock_kg += Decimal(mov.cantidad_kg or 0)
            session.delete(mov)
            return True, "Movimiento eliminado y stock revertido"

    @staticmethod
    def registrar_movimiento(
        producto_id: int,
        tipo: str,
        cantidad: Decimal,
        cantidad_kg: Decimal = Decimal("0"),
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
        if cantidad_kg < 0:
            return False, "La cantidad en KG no puede ser negativa"

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
            if tipo in ("SALIDA", "MERMA") and cantidad_kg > producto.stock_kg:
                return (
                    False,
                    f"Stock insuficiente en KG: {producto.stock_kg}",
                )

            # Update stock (und) y stock_kg
            if tipo == "ENTRADA":
                producto.stock += cantidad
                producto.stock_kg += cantidad_kg
            elif tipo == "SALIDA":
                producto.stock -= cantidad
                producto.stock_kg -= cantidad_kg
            elif tipo == "MERMA":
                producto.stock -= cantidad
                producto.stock_kg -= cantidad_kg
            elif tipo == "AJUSTE":
                producto.stock = cantidad  # absolute set
                producto.stock_kg = cantidad_kg

            costo = costo_unitario or producto.costo_unitario

            mov = MovimientoInventario(
                producto_id=producto_id,
                tipo=tipo,
                cantidad=cantidad,
                cantidad_kg=cantidad_kg,
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
