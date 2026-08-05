from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from src.database.base import Base


class UbicacionLlanta(Base):
    __tablename__ = "ubicaciones_llanta"

    id = Column(Integer, primary_key=True, index=True)

    llanta_id = Column(
        Integer, ForeignKey("llantas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    ubicacion = Column(String(100), nullable=False)

    fecha = Column(DateTime, default=datetime.utcnow)

    llanta = relationship("Llanta", back_populates="historial_ubicaciones")
