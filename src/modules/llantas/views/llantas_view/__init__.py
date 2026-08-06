"""Paquete de vistas del módulo Llantas.

Expone la API pública del monolito original ``llantas_view.py`` dividido
por responsabilidad:

- ``LlantasView``: vista principal de gestión de llantas.
- ``LlantaFormDialog``: formulario de registro de llantas.
- ``HistorialDialog``: historial de estados y ubicaciones de una llanta.
- ``CambioRapidoDialog``: cambio rápido de estado por tiquete.
"""

from src.modules.llantas.views.llantas_view._dialogs import (
    CambioRapidoDialog,
    HistorialDialog,
    LlantaFormDialog,
)
from src.modules.llantas.views.llantas_view._view import LlantasView

__all__ = [
    "CambioRapidoDialog",
    "HistorialDialog",
    "LlantaFormDialog",
    "LlantasView",
]