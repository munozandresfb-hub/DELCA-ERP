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
    """Form to register a single inventory movement.

    ENTRADA: mantiene el campo Costo Unit. y Referencia.
    SALIDA / AJUSTE: sin campo de costo (usa el costo actual del producto) y el
    campo 'Referencia' se muestra como 'Unidad de medida' (autocompletado con la
    unidad del producto seleccionado).
    """

    def __init__(self, tipo: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tipo = tipo
        self._es_salida_ajuste = tipo in ("SALIDA", "AJUSTE")
        self.setWindowTitle(self._titulo_para_tipo())
        self.resize(400, 280)
        layout = QFormLayout()

        # Product selector (se carga al final, cuando ya existen todos los widgets)
        self.producto_combo = QComboBox()
        layout.addRow("Producto *:", self.producto_combo)

        # Quantity
        self.cantidad_input = QLineEdit()
        self.cantidad_input.setPlaceholderText("0")
        layout.addRow("Cantidad *:", self.cantidad_input)

        # Cost (solo ENTRADA)
        self.costo_input: QLineEdit | None = None
        if not self._es_salida_ajuste:
            self.costo_input = QLineEdit()
            self.costo_input.setPlaceholderText("Usar costo actual del producto")
            layout.addRow("Costo Unit. $:", self.costo_input)

        # Referencia (ENTRADA) / Unidad de medida (SALIDA y AJUSTE)
        self.referencia_input = QLineEdit()
        if self._es_salida_ajuste:
            self.referencia_input.setReadOnly(True)
            self.referencia_input.setPlaceholderText("Se autocompleta con el producto")
            layout.addRow("Unidad de medida:", self.referencia_input)
        else:
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

        # Cargar productos al final (referencia_input ya existe para el autocompletado)
        self.producto_combo.currentIndexChanged.connect(self._on_producto_cambiado)
        self._cargar_productos()

    def _titulo_para_tipo(self) -> str:
        titulos = {
            "ENTRADA": "Registrar Ingreso de MP",
            "SALIDA": "Registrar Salida de MP",
            "AJUSTE": "Ajustar Stock",
        }
        return titulos.get(self._tipo, f"Registrar {self._tipo}")

    def _cargar_productos(self) -> None:
        self.producto_combo.clear()
        for p in ProductoService.listar_productos(categoria="MATERIA_PRIMA", solo_activos=True):
            label = f"{p.nombre} ({p.sku}) — Stock: {p.stock}"
            self.producto_combo.addItem(label, (p.id, p.costo_unitario, p.unidad_medida))
        self._on_producto_cambiado()

    def _on_producto_cambiado(self) -> None:
        """Autocompleta la unidad de medida para SALIDA y AJUSTE."""
        if not self._es_salida_ajuste:
            return
        data = self.producto_combo.currentData()
        if data:
            self.referencia_input.setText(str(data[2] or ""))

    def _guardar(self) -> None:
        data = self.producto_combo.currentData()
        if data is None:
            QMessageBox.warning(self, "Validación", "Seleccione un producto")
            return
        producto_id, costo_default, unidad = data

        try:
            cantidad = Decimal(self.cantidad_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad inválida")
            return

        if cantidad <= 0 and self._tipo != "AJUSTE":
            QMessageBox.warning(self, "Validación", "La cantidad debe ser > 0")
            return

        # Costo: editable solo en ENTRADA; en SALIDA/AJUSTE se usa el del producto
        if self.costo_input is not None:
            try:
                costo = Decimal(self.costo_input.text() or "0")
            except Exception:
                QMessageBox.warning(self, "Validación", "Costo inválido")
                return
            if costo == 0:
                costo = costo_default  # fallback to product's current cost
        else:
            costo = costo_default

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