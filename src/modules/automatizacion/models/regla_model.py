from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class ReglaAutomatizacion(Base):
    """Configurable automation rule."""

    __tablename__ = "reglas_automatizacion"

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('STOCK_BAJO','CARTERA_VENCIDA','LLANTAS_LISTAS')"
        ),
        CheckConstraint("nivel IN ('INFO','WARNING','CRITICAL')"),
        Index("ix_reglas_tipo", "tipo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    nivel: Mapped[str] = mapped_column(String(20), default="WARNING")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )


class Alerta(Base):
    """Generated alert from automation rules."""

    __tablename__ = "alertas"

    __table_args__ = (
        CheckConstraint("nivel IN ('INFO','WARNING','CRITICAL')"),
        Index("ix_alertas_tipo", "tipo"),
        Index("ix_alertas_leida", "leida"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    mensaje: Mapped[str] = mapped_column(String(500), nullable=False)
    nivel: Mapped[str] = mapped_column(String(20), default="INFO")
    leida: Mapped[bool] = mapped_column(Boolean, default=False)
    entidad_tipo: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    entidad_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )
