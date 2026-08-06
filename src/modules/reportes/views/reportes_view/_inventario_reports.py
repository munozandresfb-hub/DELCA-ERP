"""Métodos de la pestaña Inventario del ReportesView."""

from PySide6.QtWidgets import QTabWidget

from src.modules.reportes.services.reporte_service import ReporteService
from src.modules.reportes.views.reportes_view._report_tab import _ReportTab


class _InventarioReportView:
    """Sección Inventario: por categoría, movimientos y stock bajo."""

    def _setup_inventario_tab(self) -> None:
        tab = _ReportTab("por Categoría")
        tab.set_columns(
            ["Categoría", "Producto", "Código", "Stock", "Valor"]
        )

        tab2 = _ReportTab("Movimientos por Tipo")
        tab2.set_columns(["Consecutivo", "Tipo", "Cant. Mov.", "Unidades"])

        tab3 = _ReportTab("Stock Bajo")
        tab3.set_columns(["Producto", "SKU", "Stock"])

        self._inventario_tabs = QTabWidget()
        self._inventario_tabs.addTab(tab, "por Categoría")
        self._inventario_tabs.addTab(tab2, "Movimientos")
        self._inventario_tabs.addTab(tab3, "Stock Bajo")
        self.tabs.addTab(self._inventario_tabs, "Inventario")

    def _refresh_inventario(self) -> None:
        # por Categoría (per-product detail)
        tab = self._inventario_tabs.widget(0)
        if isinstance(tab, _ReportTab):
            tab.clear_rows()
            data = ReporteService.inventario_por_categoria()
            total_valor = 0
            for r in data:
                tab.add_row(
                    [
                        r["categoria"],
                        r["producto"],
                        str(r["codigo"]),
                        str(r["stock"]),
                        f"${r['valor']:,.2f}",
                    ]
                )
                total_valor += r["valor"]
            if data:
                tab.clear_summaries()
                tab.add_summary(
                    f"Valor total: ${total_valor:,.2f}",
                    color="#27ae60",
                )
            else:
                tab.add_row(["(sin datos)"] * 5)

        # Movimientos
        tab2 = self._inventario_tabs.widget(1)
        if isinstance(tab2, _ReportTab):
            tab2.clear_rows()
            data = ReporteService.movimientos_por_tipo()
            for r in data:
                tab2.add_row(
                    [
                        str(r["consecutivo"]),
                        r["tipo"],
                        str(r["cantidad"]),
                        str(r["total_unidades"]),
                    ]
                )
            if not data:
                tab2.add_row(["(sin datos)"] * 4)

        # Stock bajo
        tab3 = self._inventario_tabs.widget(2)
        if isinstance(tab3, _ReportTab):
            tab3.clear_rows()
            data = ReporteService.productos_stock_bajo()
            for r in data:
                tab3.add_row(
                    [
                        r["nombre"],
                        r["sku"],
                        str(r["stock"]),
                    ]
                )
            if not data:
                tab3.add_row(["(sin datos)", "", ""])