from __future__ import annotations

from typing import cast

from sqlalchemy import Column, Float, Integer, String, UniqueConstraint

from src.database.base import Base


class DimensionLlanta(Base):
    """Catálogo de dimensiones de llantas (ancho/perfil/rin)."""

    __tablename__ = "dimensiones_llanta"

    __table_args__ = (
        UniqueConstraint("ancho", "perfil", "rin", name="uq_dimension_completa"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ancho = Column(Integer, nullable=False, comment="Ancho del neumático en mm (ej. 205)")
    perfil = Column(Integer, nullable=True, comment="Perfil (ej. 55) — opcional: algunas dimensiones solo usan ancho y rin")
    rin = Column(Float, nullable=True, comment="Diámetro del rin en pulgadas (ej. 16 o 22.5) — NULL si la dimensión no aplica rin (p.ej. llantas convencionales)")

    @property
    def display(self) -> str:
        if self.rin is None:
            # Sin rin: nomenclatura convencional (p.ej. 10.00-20 -> "10-20")
            if self.perfil is None:
                return f"{self.ancho}"
            return f"{self.ancho}-{self.perfil}"
        rin_val = cast(float, self.rin)
        rin_str = (
            f"{rin_val:.1f}"
            if rin_val != int(rin_val)
            else str(int(rin_val))
        )
        if self.perfil is None:
            return f"{self.ancho} R{rin_str}"
        return f"{self.ancho}/{self.perfil} R{rin_str}"

    def __repr__(self) -> str:
        return f"<DimensionLlanta {self.display}>"
