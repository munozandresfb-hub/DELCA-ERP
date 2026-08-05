"""
Centralized configuration for DELCA ERP.

Loads from .env file with sensible defaults.
Supports future PostgreSQL by using SQLAlchemy URL format.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root is two levels up from src/config.py
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

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

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
