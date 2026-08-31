"""
Centralized configuration for DELCA ERP.

Loads from .env file with sensible defaults.
Supports future PostgreSQL by using SQLAlchemy URL format.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Project root:
#  - Modo desarrollo: dos niveles arriba de src/config.py (ruta del repo).
#  - Modo empaquetado (PyInstaller): la carpeta donde está el .exe.
#    En un exe onefile, __file__ apunta a un directorio temporal (_MEIxxx)
#    que se borra al cerrar; usar sys.executable garantiza una ruta estable.
#    Unificación de BD: si el exe está dentro de dist/ del proyecto y la BD
#    existe en la carpeta padre (el repo), se usa ESA BD — la misma que usa
#    el modo desarrollo (.bat). Si el exe es portable (sin BD en el padre),
#    usa su propia carpeta.
if getattr(sys, "frozen", False):
    _exe_dir = Path(sys.executable).resolve().parent
    _padre = _exe_dir.parent
    if (_padre / "delca.db").exists():
        PROJECT_ROOT = _padre
    else:
        PROJECT_ROOT = _exe_dir
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    # ── Database ────────────────────────────────────────────────
    # Use SQLite by default; set DATABASE_URL for PostgreSQL
    # SQLite: sqlite:///C:/path/to/delca.db
    # PostgreSQL: postgresql://user:pass@host:5432/delca
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{PROJECT_ROOT / 'delca.db'}",
    )

    DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

    @property
    def db_path(self) -> Path:
        """Returns the DB file path (only meaningful for SQLite)."""
        url = self.DATABASE_URL
        if url.startswith("sqlite:///"):
            return Path(url[10:])
        return PROJECT_ROOT / "delca.db"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    # ── Paths ────────────────────────────────────────────────────
    LOG_DIR: Path = Path(
        os.getenv("LOG_DIR", str(PROJECT_ROOT / "logs"))
    )
    BACKUP_DIR: Path = Path(
        os.getenv("BACKUP_DIR", str(PROJECT_ROOT / "backups"))
    )
    DATA_DIR: Path = Path(
        os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))
    )

    # ── Security ─────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")


settings = Settings()
