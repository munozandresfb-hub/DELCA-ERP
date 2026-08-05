from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class FacturaLlanta(Base):
    """Line item linking an invoice (factura) to a billed tire (llanta).

    Each row stores the unit price actually charged to the client for that
    tire at invoice time (precio_unitario). The invoice total is the sum of
    its items, but the total field on Factura is editable so the charged
    amount may differ from the sum (manual adjustments).
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
    llanta_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("llantas.id", ondelete="RESTRICT")
    )
    precio_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), comment="Precio de cobro de la llanta en la factura"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    factura = relationship("Factura", back_populates="llantas_detalle")
    llanta = relationship("Llanta")
