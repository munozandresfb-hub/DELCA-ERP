from __future__ import annotations

from decimal import Decimal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from src.modules.inventario.services.producto_service import ProductoService


class _MovimientoFormDialog(QDialog):
    """Form to register a single inventory movement (ENTRADA/SALIDA/MERMA/AJUSTE)."""

    def __init__(self, tipo: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tipo = tipo
        self.setWindowTitle(self._titulo_para_tipo())
        self.resize(400, 280)
        layout = QFormLayout()

        # Product selector
        self.producto_combo = QComboBox()
        self._cargar_productos()
        layout.addRow("Producto *:", self.producto_combo)

        # Quantity
        self.cantidad_input = QLineEdit()
        self.cantidad_input.setPlaceholderText("0")
        layout.addRow("Cantidad *:", self.cantidad_input)

        # Cost (optional — defaults to current product cost)
        self.costo_input = QLineEdit()
        self.costo_input.setPlaceholderText("Usar costo actual del producto")
        layout.addRow("Costo Unit. $:", self.costo_input)

        # Reference
        self.referencia_input = QLineEdit()
        self.referencia_input.setPlaceholderText("Factura, orden, nota...")
        layout.addRow("Referencia:", self.referencia_input)

        # Observations
        self.obs_input = QLineEdit()
        self.obs_input.setPlaceholderText("Observaciones opcionales")
        layout.addRow("Observaciones:", self.obs_input)

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._guardar)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

        self.setLayout(layout)

    def _titulo_para_tipo(self) -> str:
        titulos = {
            "ENTRADA": "Registrar Ingreso de MP",
            "SALIDA": "Registrar Salida de MP",
            "MERMA": "Registrar Merma",
            "AJUSTE": "Ajustar Stock",
        }
        return titulos.get(self._tipo, f"Registrar {self._tipo}")

    def _cargar_productos(self) -> None:
        self.producto_combo.clear()
        for p in ProductoService.listar_productos(categoria="MATERIA_PRIMA", solo_activos=True):
            label = f"{p.nombre} ({p.sku}) — Stock: {p.stock}"
            self.producto_combo.addItem(label, (p.id, p.costo_unitario))

    def _guardar(self) -> None:
        data = self.producto_combo.currentData()
        if data is None:
            QMessageBox.warning(self, "Validación", "Seleccione un producto")
            return
        producto_id, costo_default = data

        try:
            cantidad = Decimal(self.cantidad_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad inválida")
            return

        if cantidad <= 0 and self._tipo != "AJUSTE":
            QMessageBox.warning(self, "Validación", "La cantidad debe ser > 0")
            return

        try:
            costo = Decimal(self.costo_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Costo inválido")
            return
        if costo == 0:
            costo = costo_default  # fallback to product's current cost

        referencia = self.referencia_input.text().strip() or None
        observaciones = self.obs_input.text().strip() or None

        ok, msg = ProductoService.registrar_movimiento(
            producto_id=producto_id,
            tipo=self._tipo,
            cantidad=cantidad,
            costo_unitario=costo,
            referencia=referencia,
            observaciones=observaciones,
        )
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", str(msg))