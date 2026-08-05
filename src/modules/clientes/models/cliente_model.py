from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    nombre: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    nit: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    celular: Mapped[str | None] = mapped_column(String(50), nullable=True)

    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    ciudad: Mapped[str | None] = mapped_column(String(100), nullable=True)

    saldo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=0)
    activo: Mapped[bool | None] = mapped_column(Boolean, default=True)
    categoria_abc: Mapped[str | None] = mapped_column(String(1), default="B")

    facturas = relationship(
        "Factura", back_populates="cliente", lazy="dynamic"
    )
    llantas = relationship(
        "Llanta", back_populates="cliente", lazy="dynamic"
    )
