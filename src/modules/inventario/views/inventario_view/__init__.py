"""Vista de inventario — paquete desglosado por responsabilidad.

Preserva la API pública del antiguo ``inventario_view.py`` monolítico:
``from src.modules.inventario.views.inventario_view import InventarioView``
sigue funcionando.
"""

from src.modules.inventario.views.inventario_view._config_dialog import (
    ConfiguracionInventarioDialog,
)
from src.modules.inventario.views.inventario_view._view import InventarioView

__all__ = ["InventarioView", "ConfiguracionInventarioDialog"]