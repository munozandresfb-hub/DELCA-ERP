"""Utilidades de exportación a Excel para las vistas de reporte."""

import os

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from src.modules.reportes.services.reporte_service import ReporteService
from src.modules.reportes.views.reportes_view._report_tab import _ReportTab


class _ExportMixin(QWidget):
    """Handlers de exportación a Excel compartidos por las pestañas."""

    def _exportar_tabla(self, tab: _ReportTab, nombre_base: str) -> None:
        if not tab.table:
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, f"Guardar {nombre_base}",
            f"{nombre_base}.xlsx", "Excel (*.xlsx)",
        )
        if not ruta:
            return
        headers = []
        for ci in range(tab.table.columnCount()):
            item = tab.table.horizontalHeaderItem(ci)
            headers.append(item.text() if item else "")
        rows = []
        for ri in range(tab.table.rowCount()):
            row = []
            for ci in range(tab.table.columnCount()):
                item = tab.table.item(ri, ci)
                row.append(item.text() if item else "")
            rows.append(row)
        ok = ReporteService.exportar_excel(ruta, headers, rows)
        if ok:
            QMessageBox.information(
                self, "Exportar Excel",
                f"✓ Exportado:\n{os.path.basename(ruta)}",
            )
        else:
            QMessageBox.warning(
                self, "Exportar Excel",
                "No se pudo exportar. ¿openpyxl está instalado?",
            )