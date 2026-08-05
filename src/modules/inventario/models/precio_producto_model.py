from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class PrecioProducto(Base):
    """Master price list: production cost + 3 selling tiers per (design + dimension).

    This replaces CostoProduccionEstandar as the central price reference.
    PrecioVentaCliente is kept for per-client overrides on precio_normal.
    """

    __tablename__ = "precios_producto"

    __table_args__ = (
        UniqueConstraint(
            "dimension_id", "diseno_id", name="uq_precio_dimension_diseno"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dimension_id: Mapped[int] = mapped_column(
        ForeignKey("dimensiones_llanta.id", ondelete="CASCADE"), nullable=False
    )
    diseno_id: Mapped[int] = mapped_column(
        ForeignKey("disenos_llanta.id", ondelete="CASCADE"), nullable=False
    )
    costo_fabricacion: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    precio_minimo: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    precio_medio: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    precio_normal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )

    dimension = relationship("DimensionLlanta", lazy="joined")
    diseno = relationship("DisenoLlanta", lazy="joined")
