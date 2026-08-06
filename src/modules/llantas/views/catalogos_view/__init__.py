"""Paquete de vistas de catálogos maestros.

Expone la API pública del monolito original ``catalogos_view.py`` dividido
por responsabilidad:

- ``CatalogoMaestroDialog``: diálogo unificado de 4 pestañas (marcas,
  dimensiones, diseños de banda y causas de rechazo).
- ``CatalogosPage``: página envoltorio para la navegación lateral.
"""

from src.modules.llantas.views.catalogos_view._dialog import CatalogoMaestroDialog
from src.modules.llantas.views.catalogos_view._page import CatalogosPage

__all__ = [
    "CatalogoMaestroDialog",
    "CatalogosPage",
]