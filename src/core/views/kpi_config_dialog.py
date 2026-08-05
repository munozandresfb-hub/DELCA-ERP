from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QDoubleSpinBox,
)

from src.core.services.kpi_service import KpiService


class KpiConfigDialog(QDialog):
    """Admin dialog to configure break-even (punto de equilibrio) values."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Punto de Equilibrio (KPI)")
        self.setMinimumWidth(400)
        self._build_ui()
        self._cargar()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        title = QLabel("Establece las metas mensuales (punto de equilibrio)")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #2c3e50;")
        title.setWordWrap(True)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self._prod_spin = QSpinBox()
        self._prod_spin.setRange(1, 99999)
        self._prod_spin.setSuffix(" llantas")
        self._prod_spin.setStyleSheet("padding: 6px; font-size: 14px;")
        form.addRow("Producción mensual:", self._prod_spin)

        self._fin_spin = QDoubleSpinBox()
        self._fin_spin.setRange(1, 999999999.0)
        self._fin_spin.setDecimals(0)
        self._fin_spin.setPrefix("$ ")
        self._fin_spin.setStyleSheet("padding: 6px; font-size: 14px;")
        form.addRow("Facturación mensual:", self._fin_spin)

        layout.addLayout(form)
        layout.addSpacing(12)

        info = QLabel(
            "Estos valores se usan como meta mensual para calcular el "
            "porcentaje de cumplimiento en los KPI del Dashboard."
        )
        info.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._guardar)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _cargar(self) -> None:
        config = KpiService.obtener_config()
        if config:
            self._prod_spin.setValue(config.punto_equilibrio_produccion)
            self._fin_spin.setValue(float(config.punto_equilibrio_financiero))

    def _guardar(self) -> None:
        produccion = self._prod_spin.value()
        financiero = self._fin_spin.value()

        ok, msg = KpiService.guardar_config(produccion, financiero)
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", msg)
