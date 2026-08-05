from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    __table_args__ = (
        CheckConstraint("tipo IN ('ENTRADA','SALIDA','MERMA','AJUSTE')"),
        Index("ix_movimientos_producto_id", "producto_id"),
        Index("ix_movimientos_usuario_id", "usuario_id"),
        Index("ix_movimientos_tipo", "tipo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(String(20))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    referencia: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    observaciones: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    documento_id: Mapped[int | None] = mapped_column(
        ForeignKey("documentos_inventario.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    producto = relationship("Producto", back_populates="movimientos")
    documento = relationship("DocumentoInventario", back_populates="movimientos")
