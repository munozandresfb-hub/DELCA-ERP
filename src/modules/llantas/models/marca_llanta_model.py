from __future__ import annotations

from sqlalchemy import Column, Integer, String

from src.database.base import Base


class MarcaLlanta(Base):
    """Catálogo de marcas de llantas."""

    __tablename__ = "marcas_llanta"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    siglas = Column(String(10), unique=True, nullable=True, comment="Abreviatura (ej. GY, MCH)")

    def __repr__(self) -> str:
        return f"<MarcaLlanta {self.nombre}>"
