from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base
from src.modules.llantas.models.marca_llanta_model import MarcaLlanta  # noqa: F401
from src.modules.llantas.models.dimension_llanta_model import DimensionLlanta  # noqa: F401
from src.modules.llantas.models.diseno_llanta_model import DisenoLlanta  # noqa: F401


class Llanta(Base):
    __tablename__ = "llantas"

    __table_args__ = (
        CheckConstraint(
            "estado IN ('PENDIENTE','APTA','RECHAZADA','REENCAUCHADA','REPARADA','REPROCESO')"
        ),
        Index("ix_llantas_cliente_id", "cliente_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    tiquete: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # ── Orden de Servicio fields ───────────────────────────────────────
    numero_orden: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Número de orden de servicio")
    consecutivo: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Consecutivo")
    dot: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Código DOT del neumático")
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_ingreso: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.now, nullable=True)

    # ── Legacy free-text fields (keep for existing data, populated by catalogs below) ──
    marca: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dimension: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Catalog FKs (new) ─────────────────────────────────────────────
    marca_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("marcas_llanta.id", ondelete="SET NULL"), nullable=True
    )
    dimension_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("dimensiones_llanta.id", ondelete="SET NULL"), nullable=True
    )
    diseno_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("disenos_llanta.id", ondelete="SET NULL"), nullable=True
    )

    # ── Technical fields ──────────────────────────────────────────────
    ancho: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Ancho del neumático en mm")
    perfil: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Perfil")
    rin: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Diámetro del rin en pulgadas")
    indice_carga: Mapped[str | None] = mapped_column(String(10), nullable=True)
    velocidad: Mapped[str | None] = mapped_column(String(5), nullable=True)
    capas: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Ply rating / capas")
    peso_maximo: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Peso máximo soportado en kg")
    posicion: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Posición sugerida")
    rendimiento_km: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Rendimiento estimado en km")
    costo_produccion: Mapped[float | None] = mapped_column(Float, nullable=True)
    precio_venta: Mapped[float | None] = mapped_column(Float, nullable=True)
    asesor: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="Asesor comercial")

    # ── State & relationships ─────────────────────────────────────────
    estado: Mapped[str | None] = mapped_column(String(30), default="PENDIENTE")
    ubicacion_actual: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Última ubicación conocida (PRODUCCION/PLANTA/CLIENTE)"
    )

    # Causa de rechazo (obligatoria cuando estado = RECHAZADA, según
    # ESPECIFICACIONES_DELCA_v2.1.docx — sección 5.1)
    causa_rechazo_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("causas_rechazo.id", ondelete="SET NULL"),
        nullable=True,
        comment="Causa de rechazo asignada en inspección (obligatoria si estado = RECHAZADA)",
    )

    cliente_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cliente.id", ondelete="RESTRICT"), nullable=True)

    cliente = relationship("Cliente", back_populates="llantas", lazy="selectin")
    marca_obj = relationship(
        MarcaLlanta, foreign_keys=[marca_id], lazy="selectin"
    )
    dimension_obj = relationship(
        DimensionLlanta, foreign_keys=[dimension_id], lazy="selectin"
    )
    diseno_obj = relationship(
        DisenoLlanta, foreign_keys=[diseno_id], lazy="selectin"
    )
    causa_rechazo = relationship(
        "CausaRechazo", lazy="selectin"
    )

    historial_estados = relationship(
        "EstadoLlanta",
        back_populates="llanta",
        cascade="all, delete-orphan",
    )
    historial_ubicaciones = relationship(
        "UbicacionLlanta",
        back_populates="llanta",
        cascade="all, delete-orphan",
    )
