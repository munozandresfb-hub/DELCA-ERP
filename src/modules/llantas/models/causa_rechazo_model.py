from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class CausaRechazo(Base):
    """Catalogo de codigos y causas de rechazo de llantas."""

    __tablename__ = "causas_rechazo"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<CausaRechazo {self.codigo}: {self.descripcion}>"
