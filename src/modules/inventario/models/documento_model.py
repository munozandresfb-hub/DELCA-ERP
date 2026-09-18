from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class DocumentoInventario(Base):
    """Agrupa movimientos de inventario bajo un mismo número de documento."""

    __tablename__ = "documentos_inventario"

    __table_args__ = (
        CheckConstraint("tipo IN ('COMPRA','PRODUCCION','MERMA','AJUSTE','INGRESO','SALIDA')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_documento: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    observaciones: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    movimientos = relationship(
        "MovimientoInventario",
        back_populates="documento",
        lazy="selectin",
    )
