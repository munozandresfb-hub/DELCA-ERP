from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Integer, String, UniqueConstraint

from src.database.base import Base


# Tipos de dibujo de banda de rodamiento
TIPOS_DISENO = ("MIXTO", "TRACCION", "DIRECCIONAL")


class DisenoLlanta(Base):
    """Catálogo de dibujos/diseños de llantas, independiente de la marca.

    Cada diseño tiene un nombre y un tipo de dibujo: mixto, tracción
    o direccional. No está asociado a ninguna marca.
    """

    __tablename__ = "disenos_llanta"

    __table_args__ = (
        CheckConstraint("tipo IN ('MIXTO', 'TRACCION', 'DIRECCIONAL')"),
        UniqueConstraint("nombre", name="uq_diseno_nombre"),
    )

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, comment="Nombre del diseño (ej. MSA)")
    tipo = Column(String(20), nullable=False, default="MIXTO", comment="Tipo de dibujo: MIXTO/TRACCION/DIRECCIONAL")

    def __repr__(self) -> str:
        return f"<DisenoLlanta {self.nombre} ({self.tipo})>"
