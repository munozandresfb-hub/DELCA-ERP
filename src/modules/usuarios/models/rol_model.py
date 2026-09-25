from __future__ import annotations

from enum import Enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class RolNombre(str, Enum):
    """Nombres de rol estándar — única fuente de verdad.

    El sistema usa exactamente estos 3 roles (decisión de negocio).
    Cualquier comparación de rol DEBE usar estas constantes, nunca
    strings literales sueltos (evita bugs de capitalización como el de
    ROLE_TIMEOUTS que usaba "Gerencia"/"Operador").
    """

    ADMIN = "ADMIN"
    GERENCIA = "GERENCIA"
    OPERADOR = "OPERADOR"


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True)

    usuarios = relationship("Usuario", back_populates="rol", lazy="dynamic")
