from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class CostoProduccionEstandar(Base):
    """Standard manufacturing cost per tread design + tire dimension."""

    __tablename__ = "costos_produccion_estandar"

    __table_args__ = (
        UniqueConstraint("diseno_id", "dimension_id", name="uq_costo_diseno_dimension"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    diseno_id: Mapped[int] = mapped_column(
        ForeignKey("disenos_llanta.id", ondelete="CASCADE"), nullable=False
    )
    dimension_id: Mapped[int] = mapped_column(
        ForeignKey("dimensiones_llanta.id", ondelete="CASCADE"), nullable=False
    )
    costo_produccion: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )

    diseno = relationship("DisenoLlanta", lazy="joined")
    dimension = relationship("DimensionLlanta", lazy="joined")


class PrecioVentaCliente(Base):
    """Sale price per client + tread design + tire dimension."""

    __tablename__ = "precios_venta_cliente"

    __table_args__ = (
        UniqueConstraint(
            "cliente_id", "diseno_id", "dimension_id", name="uq_precio_cliente_diseno_dimension"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("cliente.id", ondelete="CASCADE"), nullable=False
    )
    diseno_id: Mapped[int] = mapped_column(
        ForeignKey("disenos_llanta.id", ondelete="CASCADE"), nullable=False
    )
    dimension_id: Mapped[int] = mapped_column(
        ForeignKey("dimensiones_llanta.id", ondelete="CASCADE"), nullable=False
    )
    precio_venta: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )

    cliente = relationship("Cliente", lazy="joined")
    diseno = relationship("DisenoLlanta", lazy="joined")
    dimension = relationship("DimensionLlanta", lazy="joined")


class RecetaProduccion(Base):
    """Raw material consumption per tread design + tire dimension."""

    __tablename__ = "recetas_produccion"

    __table_args__ = (
        UniqueConstraint(
            "diseno_id", "dimension_id", "producto_id",
            name="uq_receta_diseno_dimension_producto",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    diseno_id: Mapped[int] = mapped_column(
        ForeignKey("disenos_llanta.id", ondelete="CASCADE"), nullable=False
    )
    dimension_id: Mapped[int] = mapped_column(
        ForeignKey("dimensiones_llanta.id", ondelete="CASCADE"), nullable=False
    )
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos.id", ondelete="CASCADE"), nullable=False
    )
    cantidad: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    unidad: Mapped[str] = mapped_column(String(20), nullable=False, default="UNIDAD")

    diseno = relationship("DisenoLlanta", lazy="joined")
    dimension = relationship("DimensionLlanta", lazy="joined")
    producto = relationship("Producto", lazy="joined")
