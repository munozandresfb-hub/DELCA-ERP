"""Modelo de historial de conversaciones WhatsApp (contexto del agente)."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class WhatsappConversacion(Base):
    __tablename__ = "whatsapp_conversaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    telefono: Mapped[str] = mapped_column(String(20), index=True)
    direccion: Mapped[str] = mapped_column(String(10))  # "IN" (cliente→DELCA) | "OUT" (DELCA→cliente)
    contenido: Mapped[str] = mapped_column(Text)
    # "AGENTE" (respondido por IA) | "SISTEMA" (notificación automática) | "MANUAL"
    origen: Mapped[str] = mapped_column(String(10), default="AGENTE")
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # si fue manual
    fecha: Mapped[str] = mapped_column(String(30))  # ISO timestamp (naive, consistente con el sistema)