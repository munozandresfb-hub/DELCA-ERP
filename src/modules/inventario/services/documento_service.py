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
