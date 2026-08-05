from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class Factura(Base):
    __tablename__ = "facturas"

    __table_args__ = (
        CheckConstraint("estado IN ('PENDIENTE','PARCIAL','PAGADA','ANULADA','VENCIDA','GARANTIA')"),
        Index("ix_facturas_cliente_id", "cliente_id"),
        Index("ix_facturas_estado", "estado"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("cliente.id", ondelete="RESTRICT"), index=True
    )
    numero: Mapped[str] = mapped_column(String(50), unique=True)
    fecha_emision: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    saldo: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    plazo_dias: Mapped[int] = mapped_column(Integer, default=30, comment="Plazo de pago en dias")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    cliente = relationship("Cliente", back_populates="facturas")
    pagos = relationship(
        "Pago",
        back_populates="factura",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    llantas_detalle = relationship(
        "FacturaLlanta",
        back_populates="factura",
        cascade="all, delete-orphan",
    )
