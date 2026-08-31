"""Servicio de lógica de negocio de llantas.

Expone la API pública del monolito original ``llanta_service.py`` dividido
por dominio:

- ``LlantaService``: lógica de negocio de llantas, compuesta por mixins
  de gestión del ciclo de vida (``_core``) y CRUD de catálogos maestros
  (``_catalogos``).
- Constantes de dominio: ``ESTADOS_PROCESO``, ``UBICACIONES_PLANTA``,
  ``UBICACIONES_DISPLAY``, ``TRANSICIONES_VALIDAS``, ``ESTADOS_EN_PLANTA``.
"""

from src.modules.llantas.services.llanta_service._catalogos import _CatalogosMixin
from src.modules.llantas.services.llanta_service._constantes import (
    COMBINACIONES_VALIDAS,
    DISENO_REPARADA,
    ESTADOS_EN_PLANTA,
    ESTADOS_EN_PRODUCCION,
    ESTADOS_PROCESO,
    ESTADOS_TERMINADAS,
    TRANSICIONES_VALIDAS,
    UBICACIONES_CAMBIO_MANUAL,
    UBICACIONES_DISPLAY,
    UBICACIONES_PLANTA,
    VEREDICTO_UBICACION,
    VEREDICTOS_INSPECCION_FINAL,
)
from src.modules.llantas.services.llanta_service._core import _GestionLlantasMixin


class LlantaService(_GestionLlantasMixin, _CatalogosMixin):
    """Business logic for tire management."""


__all__ = [
    "COMBINACIONES_VALIDAS",
    "DISENO_REPARADA",
    "ESTADOS_EN_PLANTA",
    "ESTADOS_EN_PRODUCCION",
    "ESTADOS_PROCESO",
    "ESTADOS_TERMINADAS",
    "TRANSICIONES_VALIDAS",
    "UBICACIONES_CAMBIO_MANUAL",
    "UBICACIONES_DISPLAY",
    "UBICACIONES_PLANTA",
    "VEREDICTO_UBICACION",
    "VEREDICTOS_INSPECCION_FINAL",
    "LlantaService",
]