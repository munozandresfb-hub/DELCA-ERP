from datetime import date, datetime
from decimal import Decimal

from src.database.engine import get_session
from src.modules.inventario.models.documento_model import DocumentoInventario
from src.modules.inventario.models.movimiento_inventario_model import (
    MovimientoInventario,
)
from src.modules.inventario.services.producto_service import ProductoService


class DocumentoService:
    """Document-based grouping of inventory movements."""

    @staticmethod
    def _generar_numero(tipo: str, fecha: date) -> str:
        """Generate document number: TIPO-YYYYMMDD-NNN with daily sequence."""
        prefijo = tipo[:4].upper()
        fecha_str = fecha.strftime("%Y%m%d")
        like = f"{prefijo}-{fecha_str}-%"
        with get_session() as session:
            ultimo = (
                session.query(DocumentoInventario.numero_documento)
                .filter(DocumentoInventario.numero_documento.like(like))
                .order_by(DocumentoInventario.numero_documento.desc())
                .first()
            )
            if ultimo:
                seq = int(ultimo[0].rsplit("-", 1)[-1]) + 1
            else:
                seq = 1
        return f"{prefijo}-{fecha_str}-{seq:03d}"

    @staticmethod
    def crear_documento(
        tipo: str,
        fecha: date | None = None,
        observaciones: str | None = None,
    ) -> tuple[bool, str | DocumentoInventario]:
        """Create a new document with auto-generated number."""
        if tipo not in ("COMPRA", "PRODUCCION", "MERMA", "AJUSTE"):
            return False, f"Tipo inválido: {tipo}"
        fecha = fecha or date.today()
        numero = DocumentoService._generar_numero(tipo, fecha)
        with get_session() as session:
            doc = DocumentoInventario(
                numero_documento=numero,
                tipo=tipo,
                fecha=fecha,
                observaciones=observaciones,
            )
            session.add(doc)
            session.flush()
            session.expunge(doc)
            return True, doc

    @staticmethod
    def agregar_movimiento(
        documento_id: int,
        producto_id: int,
        tipo: str,
        cantidad: Decimal,
        costo_unitario: Decimal | None = None,
        referencia: str | None = None,
        observaciones: str | None = None,
    ) -> tuple[bool, str]:
        """Register a movimiento under an existing document."""
        return ProductoService.registrar_movimiento(
            producto_id=producto_id,
            tipo=tipo,
            cantidad=cantidad,
            costo_unitario=costo_unitario,
            referencia=referencia,
            observaciones=observaciones,
            documento_id=documento_id,
        )

    @staticmethod
    def buscar_documentos(
        numero: str | None = None,
        tipo: str | None = None,
        fecha_desde: date | None = None,
        fecha_hasta: date | None = None,
        limite: int = 100,
    ) -> list[DocumentoInventario]:
        """Search documents by filters."""
        with get_session() as session:
            q = session.query(DocumentoInventario)
            if numero:
                q = q.filter(
                    DocumentoInventario.numero_documento.ilike(f"%{numero}%")
                )
            if tipo:
                q = q.filter(DocumentoInventario.tipo == tipo)
            if fecha_desde:
                q = q.filter(DocumentoInventario.fecha >= fecha_desde)
            if fecha_hasta:
                q = q.filter(DocumentoInventario.fecha <= fecha_hasta)
            docs = q.order_by(
                DocumentoInventario.fecha.desc(),
                DocumentoInventario.numero_documento.desc(),
            ).limit(limite).all()
            for d in docs:
                session.expunge(d)
            return docs

    @staticmethod
    def obtener_documento(
        documento_id: int,
    ) -> DocumentoInventario | None:
        """Get a document with its movements."""
        with get_session() as session:
            doc = (
                session.query(DocumentoInventario)
                .filter(DocumentoInventario.id == documento_id)
                .first()
            )
            if doc:
                session.expunge(doc)
            return doc

    @staticmethod
    def obtener_movimientos_por_documento(
        documento_id: int,
    ) -> list[MovimientoInventario]:
        """Get all movements for a document, with eager-loaded products."""
        from sqlalchemy.orm import joinedload

        with get_session() as session:
            movs = (
                session.query(MovimientoInventario)
                .options(joinedload(MovimientoInventario.producto))
                .filter(MovimientoInventario.documento_id == documento_id)
                .order_by(MovimientoInventario.id)
                .all()
            )
            for m in movs:
                session.expunge(m)
            return movs

    @staticmethod
    def eliminar_documento(documento_id: int) -> tuple[bool, str]:
        """Delete a document and unlink its movements."""
        with get_session() as session:
            doc = (
                session.query(DocumentoInventario)
                .filter(DocumentoInventario.id == documento_id)
                .first()
            )
            if not doc:
                return False, "Documento no encontrado"
            # Unlink movements
            session.query(MovimientoInventario).filter(
                MovimientoInventario.documento_id == documento_id
            ).update(
                {MovimientoInventario.documento_id: None}
            )
            session.delete(doc)
            return True, f"Documento {doc.numero_documento} eliminado"
