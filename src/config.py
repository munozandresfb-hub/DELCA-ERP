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

    # Control de acceso basado en roles (RBAC):
    # - false (default): modo SHADOW — los denials se registran en el log
    #   pero NO se bloquean. Permite validar la matriz de permisos sin
    #   interrumpir la operación (estrategia expand-contract).
    # - true: enforcement activo — los denials bloquean la acción.
    RBAC_ENFORCE: bool = os.getenv("RBAC_ENFORCE", "false").lower() == "true"

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

    # ── WhatsApp Cloud API + Agente IA (módulo whatsapp) ──────────
    # Token de acceso permanente de la app Meta (system user token).
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    # ID del número de teléfono (phone_number_id) en Meta Business.
    WHATSAPP_PHONE_ID: str = os.getenv("WHATSAPP_PHONE_ID", "")
    # Token de verificación del webhook (lo defines tú, se repite en Meta).
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    # App secret de la app Meta — verifica la firma X-Hub-Signature-256.
    WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET", "")
    # Versión de la Graph API de Meta (ajustar a la vigente).
    WHATSAPP_GRAPH_VERSION: str = os.getenv("WHATSAPP_GRAPH_VERSION", "v21.0")

    # Agente IA (OpenAI)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Respuesta máxima del agente (charla corta por WhatsApp).
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "300"))
    # Habilita el procesamiento automático de mensajes entrantes (false = solo envío).
    WHATSAPP_AGENT_ENABLED: bool = os.getenv("WHATSAPP_AGENT_ENABLED", "false").lower() == "true"
    # Puerto local del servidor webhook (el túnel público apunta aquí).
    WHATSAPP_WEBHOOK_PORT: int = int(os.getenv("WHATSAPP_WEBHOOK_PORT", "9090"))


settings = Settings()
