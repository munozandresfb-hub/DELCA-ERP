from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class FacturaLlanta(Base):
    """Line item linking an invoice (factura) to a billed tire (llanta).

    Each row stores the unit price actually charged to the client for that
    tire at invoice time (precio_unitario). The invoice total is the sum of
    its items, but the total field on Factura is editable so the charged
    amount may differ from the sum (manual adjustments).

    ``llanta_id`` is NULL for "llanta nueva" (new tire sold without a
    re-tread process record); in that case ``descripcion`` holds the free-text
    tire description entered manually at invoice time.
    """

    __tablename__ = "factura_llantas"

    __table_args__ = (
        Index("ix_factura_llantas_factura_id", "factura_id"),
        Index("ix_factura_llantas_llanta_id", "llanta_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    factura_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("facturas.id", ondelete="CASCADE")
    )
    llanta_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("llantas.id", ondelete="RESTRICT"),
        nullable=True,
        comment="NULL cuando el item es una llanta nueva manual (solo descripcion)",
    )
    descripcion: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Descripcion libre de llanta nueva (sin registro en llantas)",
    )
    precio_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="Precio de cobro de la llanta en la factura"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    factura = relationship("Factura", back_populates="llantas_detalle")
    llanta = relationship("Llanta")
