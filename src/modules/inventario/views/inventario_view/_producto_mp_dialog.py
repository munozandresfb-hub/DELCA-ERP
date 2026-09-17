"""Diálogo para crear productos de materia prima en el inventario."""

from decimal import Decimal

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from src.modules.inventario.services.producto_service import ProductoService


class _CrearProductoMPDialog(QDialog):
    """Rápido formulario para crear productos de materia prima desde inventario."""

    UNIDADES = ["UNIDAD", "KG", "LT", "CAJA", "PAQ", "ROLLO"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nuevo Producto - Materia Prima")
        self.resize(380, 320)
        layout = QFormLayout()

        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Nombre único del producto")
        layout.addRow("Nombre *:", self.nombre_input)

        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("Código / SKU")
        layout.addRow("Código *:", self.sku_input)

        self.precio_input = QLineEdit()
        self.precio_input.setPlaceholderText("0.00")
        layout.addRow("Costo Unitario $:", self.precio_input)

        self.cantidad_input = QLineEdit()
        self.cantidad_input.setPlaceholderText("0")
        layout.addRow("Cantidad en planta Und:", self.cantidad_input)

        self.stock_kg_input = QLineEdit()
        self.stock_kg_input.setPlaceholderText("0")
        layout.addRow("Cantidad en planta en KG:", self.stock_kg_input)

        self.minimo_input = QLineEdit()
        self.minimo_input.setPlaceholderText("0")
        layout.addRow("Mínimo en planta:", self.minimo_input)

        self.unidad_combo = QComboBox()
        self.unidad_combo.addItems(self.UNIDADES)
        layout.addRow("Unidad de medida:", self.unidad_combo)

        self.fecha_input = QDateEdit()
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setDate(QDate.currentDate())
        layout.addRow("Fecha de ingreso:", self.fecha_input)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._guardar)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

        self.setLayout(layout)

    def _guardar(self) -> None:
        nombre = self.nombre_input.text().strip()
        sku = self.sku_input.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio")
            return
        if not sku:
            QMessageBox.warning(self, "Validación", "El código/SKU es obligatorio")
            return

        try:
            precio = Decimal(self.precio_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Precio inválido")
            return

        try:
            cantidad = Decimal(self.cantidad_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad inválida")
            return
        if cantidad < 0:
            QMessageBox.warning(self, "Validación", "La cantidad no puede ser negativa")
            return

        try:
            stock_kg = Decimal(self.stock_kg_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad en KG inválida")
            return
        if stock_kg < 0:
            QMessageBox.warning(self, "Validación", "La cantidad en KG no puede ser negativa")
            return

        try:
            minimo = Decimal(self.minimo_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Mínimo inválido")
            return
        if minimo < 0:
            QMessageBox.warning(self, "Validación", "El mínimo no puede ser negativo")
            return

        ok, resultado = ProductoService.crear(
            nombre=nombre,
            sku=sku,
            categoria="MATERIA_PRIMA",
            costo_unitario=precio,
            stock_inicial=cantidad,
            stock_kg=stock_kg,
            stock_minimo=minimo,
            unidad_medida=self.unidad_combo.currentText(),
        )
        if ok:
            QMessageBox.information(self, "Éxito", f"Producto '{nombre}' creado")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", str(resultado))

    def get_data(self) -> dict:
        return {
            "nombre": self.nombre_input.text().strip(),
            "sku": self.sku_input.text().strip(),
            "categoria": "MATERIA_PRIMA",
            "costo_unitario": Decimal(self.precio_input.text() or "0"),
            "stock_inicial": Decimal(self.cantidad_input.text() or "0"),
            "stock_kg": Decimal(self.stock_kg_input.text() or "0"),
            "stock_minimo": Decimal(self.minimo_input.text() or "0"),
            "unidad_medida": self.unidad_combo.currentText(),
        }