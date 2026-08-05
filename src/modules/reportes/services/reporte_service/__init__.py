"""Servicio de reportes — fachada multi-dominio.

Preserva la API pública del antiguo ``reporte_service.py`` monolítico:
``from src.modules.reportes.services.reporte_service import ReporteService``
sigue funcionando con los mismos métodos estáticos.
"""

from src.modules.reportes.services.reporte_service._clientes import _ClientesReports
from src.modules.reportes.services.reporte_service._dashboard import _DashboardReports
from src.modules.reportes.services.reporte_service._export import _ExportMixin
from src.modules.reportes.services.reporte_service._facturas import _FacturasReports
from src.modules.reportes.services.reporte_service._inventario import _InventarioReports
from src.modules.reportes.services.reporte_service._llantas import _LlantasReports


class ReporteService(
    _ClientesReports,
    _LlantasReports,
    _FacturasReports,
    _InventarioReports,
    _DashboardReports,
    _ExportMixin,
):
    """Report generation service with cross-module queries."""


__all__ = ["ReporteService"]
