from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)

    nombre: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))

    # ── Security fields ────────────────────────────────────────────
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    requires_password_change: Mapped[bool] = mapped_column(
        Boolean, default=False
    )
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    rol = relationship("Rol", back_populates="usuarios")