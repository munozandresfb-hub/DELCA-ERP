from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class KpiConfig(Base):
    """Singleton configuration for break-even (punto de equilibrio) values."""

    __tablename__ = "kpi_config"

    __table_args__ = (
        UniqueConstraint("id", name="uq_kpi_config_singleton"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    punto_equilibrio_produccion: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100,
        comment="Meta mensual de llantas producidas",
    )
    punto_equilibrio_financiero: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=1000000.0,
        comment="Meta mensual de facturación en $",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )


class KpiHistorico(Base):
    """Monthly KPI record: actual production & invoicing vs break-even."""

    __tablename__ = "kpi_historico"

    __table_args__ = (
        UniqueConstraint("anio", "mes", name="uq_kpi_mes"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    mes: Mapped[int] = mapped_column(Integer, nullable=False)
    llantas_producidas: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    facturacion_total: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0.0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )
