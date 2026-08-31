from __future__ import annotations

from typing import cast

from sqlalchemy import Column, Float, Integer, String, UniqueConstraint

from src.database.base import Base


class DimensionLlanta(Base):
    """Catálogo de dimensiones de llantas (ancho/perfil/rin + sufijo)."""

    __tablename__ = "dimensiones_llanta"

    __table_args__ = (
        UniqueConstraint(
            "ancho", "perfil", "rin", "sufijo", name="uq_dimension_completa"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    ancho = Column(
        Float, nullable=True,
        comment="Ancho del neumático en mm (ej. 295) o pulgadas (ej. 9.5). NULL para formatos sin ancho (ej. H78-15)."
    )
    perfil = Column(Integer, nullable=True, comment="Perfil (ej. 55) — opcional: algunas dimensiones solo usan ancho y rin")
    rin = Column(Float, nullable=True, comment="Diámetro del rin en pulgadas (ej. 16 o 22.5) — NULL si la dimensión no aplica rin (p.ej. llantas convencionales)")
    sufijo = Column(
        String(10), nullable=False, default="", server_default="",
        comment="Sufijo visible en la dimensión (ej. C, U). Vacío si no aplica.",
    )

    @property
    def display(self) -> str:
        sufijo = self.sufijo or ""
        if self.rin is None:
            # Sin rin: nomenclatura convencional (p.ej. 10.00-20 -> "10-20")
            if self.perfil is None:
                return f"{self._fmt_num(self.ancho)}{sufijo}"
            return f"{self._fmt_num(self.ancho)}-{self.perfil}{sufijo}"
        rin_val = cast(float, self.rin)
        rin_str = (
            f"{rin_val:.1f}"
            if rin_val != int(rin_val)
            else str(int(rin_val))
        )
        if self.perfil is None:
            return f"{self._fmt_num(self.ancho)} R{rin_str}{sufijo}"
        return f"{self._fmt_num(self.ancho)}/{self.perfil} R{rin_str}{sufijo}"

    @staticmethod
    def _fmt_num(val) -> str:
        """Formatea un número: 9.5 -> '9.5', 295.0 -> '295', 8.25 -> '8.25'."""
        if val is None:
            return ""
        v = float(val)
        if v == int(v):
            return str(int(v))
        # Conservar hasta 2 decimales, sin ceros finales (9.50 -> '9.5')
        s = f"{v:.2f}".rstrip("0").rstrip(".")
        return s

    def __repr__(self) -> str:
        return f"<DimensionLlanta {self.display}>"
