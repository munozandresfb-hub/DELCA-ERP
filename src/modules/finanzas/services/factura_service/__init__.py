from src.modules.finanzas.services.factura_service._cartera import _CarteraMixin
from src.modules.finanzas.services.factura_service._facturas import _FacturasMixin
from src.modules.finanzas.services.factura_service._pagos import _PagosMixin


class FacturaService(_FacturasMixin, _PagosMixin, _CarteraMixin):
    """Business logic for invoice (factura) management."""


__all__ = ["FacturaService"]