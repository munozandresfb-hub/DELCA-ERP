from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.modules.finanzas.models.factura_model import Factura


class PagoDialog(QDialog):
    """Dialog for registering a payment against an invoice."""

    def __init__(
        self, factura: Factura, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.factura = factura
        self.setWindowTitle(f"Registrar Pago - {factura.numero}")
        self.resize(400, 250)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        form = QFormLayout()

        info = QLabel(
            f"Factura: {self.factura.numero}\n"
            f"Total: ${self.factura.total:,.2f}\n"
            f"Saldo pendiente: ${self.factura.saldo:,.2f}"
        )
        info.setStyleSheet(
            "font-size: 14px; padding: 10px; background: #f8f9fa;"
            "border-radius: 6px;"
        )
        layout.addWidget(info)

        self.valor_input = QLineEdit()
        self.valor_input.setPlaceholderText(
            f"0.00 (máx: ${self.factura.saldo:,.2f})"
        )
        form.addRow("Valor *:", self.valor_input)

        self.metodo_combo = QComboBox()
        self.metodo_combo.addItems(
            ["EFECTIVO", "TRANSFERENCIA", "TARJETA", "CHEQUE", "OTRO"]
        )
        form.addRow("Método:", self.metodo_combo)

        self.referencia_input = QLineEdit()
        self.referencia_input.setPlaceholderText("N° de referencia (opcional)")
        form.addRow("Referencia:", self.referencia_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        pagar_btn = QPushButton("Registrar Pago")
        pagar_btn.clicked.connect(self._guardar)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addWidget(pagar_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _guardar(self) -> None:
        valor_text = self.valor_input.text().strip()
        if not valor_text:
            QMessageBox.warning(self, "Validación", "Ingrese el valor del pago")
            return
        try:
            valor = Decimal(valor_text)
        except Exception:
            QMessageBox.warning(self, "Validación", "Valor inválido")
            return
        if valor <= 0:
            QMessageBox.warning(
                self, "Validación", "El valor debe ser mayor a cero"
            )
            return
        if valor > self.factura.saldo:
            QMessageBox.warning(
                self,
                "Validación",
                f"El pago no puede superar el saldo (${self.factura.saldo:,.2f})",
            )
            return
        self.accept()

    def get_data(
        self,
    ) -> tuple[Decimal, str, str | None]:
        return (
            Decimal(self.valor_input.text().strip()),
            self.metodo_combo.currentText(),
            self.referencia_input.text().strip() or None,
        )