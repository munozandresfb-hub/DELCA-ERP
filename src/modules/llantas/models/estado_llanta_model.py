from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from src.database.base import Base


class EstadoLlanta(Base):
    __tablename__ = "estados_llanta"

    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE','APTA','RECHAZADA','REENCAUCHADA','REPARADA')"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    llanta_id = Column(
        Integer, ForeignKey("llantas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    estado = Column(String(30), nullable=False)

    fecha = Column(DateTime, default=datetime.utcnow)

    llanta = relationship("Llanta", back_populates="historial_estados")
