"""Configuración centralizada de logging para DELCA ERP.

Restaura la observabilidad en producción:
- Log rotativo a %LOCALAPPDATA%/DELCA/logs/delca.log (5 MB × 5 backups).
- Root logger a INFO.
- sys.excepthook que loguea el traceback completo y muestra un mensaje amigable.
- Redirección de stdout/stderr al log (la app corre con pythonw, sin consola).

Uso: importar y llamar setup_logging() como PRIMERA línea del main().
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

_LOG_NAME = "delca.log"
_MAX_BYTES = 5_000_000
_BACKUP_COUNT = 5


def get_log_dir() -> Path:
    """Directorio de logs: %LOCALAPPDATA%/DELCA/logs (nunca junto al exe ni en OneDrive)."""
    local_appdata = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local_appdata) / "DELCA" / "logs"


def get_log_path() -> Path:
    """Ruta absoluta del archivo de log activo."""
    return get_log_dir() / _LOG_NAME


class _Tee:
    """Redirige stdout/stderr al log de la app (captura print() residuales).

    Escribe en el archivo de log con nivel INFO (stdout) / ERROR (stderr)
    y, si hay consola real, también refleja en ella.
    """

    def __init__(self, stream_name: str, level: int) -> None:
        self._name = stream_name
        self._level = level
        self._original = getattr(sys, stream_name)

    def write(self, message: str) -> int:
        if message and not message.isspace():
            logging.log(self._level, "[%s] %s", self._name, message.rstrip())
        if self._original is not None and self._original != sys.__stdout__:
            try:
                self._original.write(message)
            except Exception:
                pass
        return len(message)

    def flush(self) -> None:
        if self._original is not None and hasattr(self._original, "flush"):
            try:
                self._original.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        return False


def setup_logging() -> None:
    """Configura el logging global. Idempotente: no duplica handlers si se llama dos veces."""
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Evitar handlers duplicados si setup_logging se invoca más de una vez
    for h in list(root.handlers):
        if getattr(h, "_delca_managed", False):
            return

    handler = logging.handlers.RotatingFileHandler(
        get_log_path(),
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    handler._delca_managed = True  # type: ignore[attr-defined]
    root.addHandler(handler)

    # Excepthook global: log completo + mensaje amigable
    def _excepthook(exc_type, exc_value, exc_tb):
        logging.getLogger("delca.uncaught").error(
            "Excepción no controlada: %s",
            exc_value,
            exc_info=(exc_type, exc_value, exc_tb),
        )
        try:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                None,
                "Error inesperado",
                "DELCA ERP encontró un error inesperado.\n\n"
                f"Consulte el log en:\n{get_log_path()}",
            )
        except Exception:
            pass  # Si la GUI no está disponible, solo queda el log

    sys.excepthook = _excepthook

    # Redirección de stdout/stderr (la app se lanza con pythonw sin consola)
    sys.stdout = _Tee("stdout", logging.INFO)
    sys.stderr = _Tee("stderr", logging.ERROR)