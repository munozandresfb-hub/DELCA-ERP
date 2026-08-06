from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.modules.finanzas.models.factura_model import Factura


class AbonosDialog(QDialog):
    """Dialog showing payment history for an invoice."""

    def __init__(self, factura: Factura, pagos: list, parent=None):
        super().__init__(parent)
        self.factura = factura
        self.setWindowTitle(f"Abonos - {factura.numero}")
        self.resize(550, 320)
        self.setup_ui(pagos)

    def setup_ui(self, pagos):
        layout = QVBoxLayout()

        info = QLabel(
            f"Factura: {self.factura.numero}  |  "
            f"Total: ${self.factura.total:,.2f}  |  "
            f"Saldo: ${self.factura.saldo:,.2f}  |  "
            f"Plazo: {self.factura.plazo_dias or 30} d\u00edas"
        )
        info.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px;")
        layout.addWidget(info)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Fecha", "M\u00e9todo", "Referencia", "Valor"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)

        table.setRowCount(len(pagos))
        for row, p in enumerate(pagos):
            table.setItem(row, 0, QTableWidgetItem(p.fecha.strftime("%Y-%m-%d %H:%M")))
            table.setItem(row, 1, QTableWidgetItem(p.metodo_pago))
            table.setItem(row, 2, QTableWidgetItem(p.referencia or "\u2014"))
            table.setItem(row, 3, QTableWidgetItem(f"${p.valor:,.2f}"))

        layout.addWidget(table)

        cerrar = QPushButton("Cerrar")
        cerrar.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        cerrar.clicked.connect(self.accept)
        layout.addWidget(cerrar)

        self.setLayout(layout)