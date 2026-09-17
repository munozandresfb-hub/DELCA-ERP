from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class Producto(Base):
    __tablename__ = "productos"

    __table_args__ = (
        CheckConstraint("unidad_medida IN ('UNidad','KG','LT','MT','CAJA','PAQ')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    categoria: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    stock: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    stock_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    costo_unitario: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0
    )
    precio_venta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0
    )
    stock_minimo: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0
    )
    unidad_medida: Mapped[str] = mapped_column(String(20), default="UNidad")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    movimientos = relationship(
        "MovimientoInventario",
        back_populates="producto",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
