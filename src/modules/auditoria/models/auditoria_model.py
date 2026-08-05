from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    __table_args__ = (
        CheckConstraint("accion IN ('CREATE','UPDATE','DELETE','LOGIN','LOGOUT','FALLO_LOGIN')"),
        Index("ix_auditoria_usuario_id", "usuario_id"),
        Index("ix_auditoria_entidad", "entidad"),
        Index("ix_auditoria_accion", "accion"),
        Index("ix_auditoria_fecha", "fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True
    )
    entidad: Mapped[str] = mapped_column(String(100))
    accion: Mapped[str] = mapped_column(String(20))
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_origen: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )
