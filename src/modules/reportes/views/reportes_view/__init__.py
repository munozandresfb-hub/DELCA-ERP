"""Vista de reportes — paquete desglosado por dominio.

Preserva la API pública del antiguo ``reportes_view.py`` monolítico:
``from src.modules.reportes.views.reportes_view import ReportesView``
sigue funcionando.
"""

from src.modules.reportes.views.reportes_view._clientes_reports import (
    _ClientesReportView,
)
from src.modules.reportes.views.reportes_view._export import _ExportMixin
from src.modules.reportes.views.reportes_view._finanzas_reports import (
    _FinanzasReportView,
)
from src.modules.reportes.views.reportes_view._indicadores_reports import (
    _IndicadoresReportView,
)
from src.modules.reportes.views.reportes_view._inventario_reports import (
    _InventarioReportView,
)
from src.modules.reportes.views.reportes_view._llantas_reports import (
    _LlantasReportView,
)
from src.modules.reportes.views.reportes_view._report_tab import _ReportTab
from src.modules.reportes.views.reportes_view._resumen_reports import (
    _ResumenReportView,
)

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class ReportesView(
    _ClientesReportView,
    _LlantasReportView,
    _IndicadoresReportView,
    _FinanzasReportView,
    _InventarioReportView,
    _ResumenReportView,
    _ExportMixin,
    QWidget,
):
    """Multi-tab report view."""

    def __init__(self) -> None:
        super().__init__()
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # Header
        header = QLabel("Reportes")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px 0;"
        )
        layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        refresh_btn = QPushButton("🔄 Actualizar Todos")
        refresh_btn.clicked.connect(self._refresh_all)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)

        # Tabs
        self.tabs = QTabWidget()

        self._setup_clientes_tab()
        self._setup_llantas_tab()
        self._setup_indicadores_tab()
        self._setup_finanzas_tab()
        self._setup_inventario_tab()
        self._setup_resumen_tab()

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # ── Carga diferida (lazy): solo la pestaña visible carga al abrir;
        # las demás cargan al seleccionarse por primera vez. Acelera la
        # apertura del módulo (evita ~13 queries pesadas al arrancar).
        self._tabs_cargadas: set[int] = set()
        self.tabs.currentChanged.connect(self._on_tab_change)
        self._on_tab_change(self.tabs.currentIndex())

    def _on_tab_change(self, idx: int) -> None:
        """Refresca la pestaña seleccionada la primera vez que se muestra."""
        if idx in self._tabs_cargadas:
            return
        self._tabs_cargadas.add(idx)
        refreshers = {
            0: self._refresh_clientes,
            1: self._refresh_reporte_llantas,
            2: self._refresh_indicadores,
            3: self._refresh_finanzas,
            4: self._refresh_inventario,
            5: self._refresh_resumen,
        }
        fn = refreshers.get(idx)
        if fn:
            fn()

    def _refresh_all(self) -> None:
        self._refresh_clientes()
        self._refresh_reporte_llantas()
        self._refresh_indicadores()
        self._refresh_finanzas()
        self._refresh_inventario()
        self._refresh_resumen()
        self._tabs_cargadas = {0, 1, 2, 3, 4, 5}


__all__ = ["ReportesView", "_ReportTab"]