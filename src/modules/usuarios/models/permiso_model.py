from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


# ── Association table: Rol → Permiso ──────────────────────────────────
rol_permiso = Table(
    "roles_permisos",
    Base.metadata,
    Column("rol_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permiso_id", Integer, ForeignKey("permisos.id", ondelete="CASCADE"), primary_key=True),
)


class Permiso(Base):
    """Individual permission (e.g. 'clientes.crear', 'reportes.ver')."""

    __tablename__ = "permisos"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
