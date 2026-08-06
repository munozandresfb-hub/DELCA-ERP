"""Métodos de la pestaña Resumen del ReportesView."""

from src.modules.reportes.services.reporte_service import ReporteService
from src.modules.reportes.views.reportes_view._report_tab import _ReportTab


class _ResumenReportView:
    """Sección Resumen general del ReportesView."""

    def _setup_resumen_tab(self) -> None:
        tab = _ReportTab("Resumen General")
        tab.set_columns(["Métrica", "Valor"])
        self.tabs.addTab(tab, "Resumen")

    def _refresh_resumen(self) -> None:
        tab = self.tabs.widget(5)  # Resumen tab
        if isinstance(tab, _ReportTab):
            tab.clear_rows()
            data = ReporteService.obtener_resumen_completo()
            tab.add_row(["Clientes Activos", str(data["clientes_activos"])])
            tab.add_row(["Clientes Inactivos", str(data["clientes_inactivos"])])
            tab.add_row(["Total Clientes", str(data["total_clientes"])])
            tab.add_row(["Llantas en Planta", str(data["llantas_en_planta"])])
            tab.add_row(["Total Llantas (histórico)", str(data["total_llantas"])])
            tab.add_row(["Facturas Pendientes", str(data["facturas_pendientes"])])
            tab.add_row(["Total Facturas", str(data["total_facturas"])])
            tab.add_row(["Productos Stock Bajo", str(data["productos_stock_bajo"])])
            tab.add_row(["Total Productos", str(data["total_productos"])])
            tab.add_row(["Total Pagos", str(data["total_pagos"])])
            tab.add_row(
                [
                    "Total Mov. Inventario",
                    str(data["total_movimientos"]),
                ]
            )
            tab.add_row(
                [
                    "Facturación Anual",
                    f"${data['facturacion_anual']:,.2f}",
                ]
            )
            tab.add_row(
                [
                    "Valor Inventario",
                    f"${data['valor_inventario']:,.2f}",
                ]
            )