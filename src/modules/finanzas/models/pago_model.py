from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class Pago(Base):
    __tablename__ = "pagos"

    __table_args__ = (
        CheckConstraint(
            "metodo_pago IN ('EFECTIVO','TRANSFERENCIA','CHEQUE','TARJETA')"
        ),
        Index("ix_pagos_factura_id", "factura_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    factura_id: Mapped[int] = mapped_column(
        ForeignKey("facturas.id", ondelete="CASCADE")
    )
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    metodo_pago: Mapped[str] = mapped_column(String(30), default="EFECTIVO")
    referencia: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    factura = relationship("Factura", back_populates="pagos")
