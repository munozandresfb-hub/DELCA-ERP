"""Ventana emergente de abonos de un cliente (módulo Cartera).

Mismo formato que el detalle de abonos de Facturación, pero agrupando los
pagos de todas las facturas del cliente (con el número de factura).
"""

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AbonosClienteDialog(QDialog):
    """Lista los abonos (pagos) de todas las facturas de un cliente."""

    def __init__(
        self,
        cliente_nombre: str,
        abonos: list[dict],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.abonos = abonos
        self.setWindowTitle(f"Abonos - {cliente_nombre}")
        self.resize(620, 360)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        total_abonado = sum(a["valor"] for a in self.abonos)
        info = QLabel(
            f"Cliente: {self.windowTitle().replace('Abonos - ', '')}  |  "
            f"Total abonado: ${total_abonado:,.2f}  |  "
            f"{len(self.abonos)} abono(s)"
        )
        info.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px;")
        layout.addWidget(info)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(
            ["Factura", "Fecha", "M\u00e9todo", "Referencia", "Valor"]
        )
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)

        table.setRowCount(len(self.abonos))
        for row, a in enumerate(self.abonos):
            table.setItem(row, 0, QTableWidgetItem(a["factura_numero"]))
            table.setItem(
                row,
                1,
                QTableWidgetItem(a["fecha"].strftime("%Y-%m-%d %H:%M")),
            )
            table.setItem(row, 2, QTableWidgetItem(a["metodo_pago"]))
            table.setItem(row, 3, QTableWidgetItem(a["referencia"] or "\u2014"))
            table.setItem(row, 4, QTableWidgetItem(f"${a['valor']:,.2f}"))

        layout.addWidget(table)

        btn_layout = QHBoxLayout()
        cerrar = QPushButton("Cerrar")
        cerrar.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        cerrar.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(cerrar)
        layout.addLayout(btn_layout)

        self.setLayout(layout)