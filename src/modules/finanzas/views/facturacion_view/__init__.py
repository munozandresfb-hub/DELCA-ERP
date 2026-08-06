"""Paquete de vistas de facturación.

Expone la API pública de las 4 clases del monolito original
``facturacion_view.py`` divididas por responsabilidad:

- ``FacturaFormDialog``: formulario de creación de facturas.
- ``PagoDialog``: registro de pagos contra una factura.
- ``AbonosDialog``: historial de pagos de una factura.
- ``FacturacionView``: vista principal de gestión de facturas.
"""

from src.modules.finanzas.views.facturacion_view._abonos_dialog import AbonosDialog
from src.modules.finanzas.views.facturacion_view._factura_form_dialog import (
    FacturaFormDialog,
)
from src.modules.finanzas.views.facturacion_view._pago_dialog import PagoDialog
from src.modules.finanzas.views.facturacion_view._view import FacturacionView

__all__ = [
    "AbonosDialog",
    "FacturaFormDialog",
    "PagoDialog",
    "FacturacionView",
]