"""Diálogo para crear productos (materia prima o consumible) en el inventario."""

from decimal import Decimal

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
)

from src.modules.inventario.services.producto_service import ProductoService

# Estilo de los botones tipo pestaña (consistente con el QTabWidget de la vista)
_ESTILO_TAB = """
QPushButton {{
    background: #f0f0f0;
    border: 1px solid #d0d0d0;
    border-bottom: 2px solid #d0d0d0;
    border-radius: 4px 4px 0 0;
    padding: 6px 14px;
    font-weight: bold;
    color: #555;
}}
QPushButton:checked {{
    background: #ffffff;
    border-bottom: 3px solid {color};
    color: {color};
}}
"""


class _CrearProductoDialog(QDialog):
    """Rápido formulario para crear productos de materia prima o consumible.

    Permite seleccionar el tipo de producto con un click sobre el recuadro
    correspondiente (Materia Prima / Consumible); la categoría guardada se
    deriva de la selección.
    """

    UNIDADES = ["UNIDAD", "KG", "LT", "CAJA", "PAQ", "ROLLO"]
    TIPOS = {
        "MATERIA_PRIMA": "Materia Prima",
        "CONSUMIBLE": "Consumible",
    }
    COLOR_TIPO = {
        "MATERIA_PRIMA": "#3498db",
        "CONSUMIBLE": "#27ae60",
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        categoria_inicial: str = "MATERIA_PRIMA",
    ) -> None:
        super().__init__(parent)
        self._categoria = (
            categoria_inicial if categoria_inicial in self.TIPOS else "MATERIA_PRIMA"
        )
        self.setWindowTitle(f"Nuevo Producto - {self.TIPOS[self._categoria]}")
        self.resize(380, 360)
        layout = QFormLayout()

        # ── Selector de tipo de producto (botones tipo pestaña) ──
        tipo_row = QHBoxLayout()
        tipo_row.setSpacing(6)
        self._tipo_group = QButtonGroup(self)
        self._tipo_group.setExclusive(True)
        self._botones_tipo: dict[str, QPushButton] = {}
        for idx, (cat, label) in enumerate(self.TIPOS.items()):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(_ESTILO_TAB.format(color=self.COLOR_TIPO[cat]))
            btn.setChecked(cat == self._categoria)
            self._tipo_group.addButton(btn, idx)
            self._botones_tipo[cat] = btn
            tipo_row.addWidget(btn)
        self._tipo_group.idClicked.connect(self._cambiar_tipo)
        tipo_widget = QWidget()
        tipo_widget.setLayout(tipo_row)
        layout.addRow("Tipo de producto:", tipo_widget)

        # ── Campos del formulario ──
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

    def _cambiar_tipo(self, id_boton: int) -> None:
        """Actualiza la categoría activa según el botón de tipo seleccionado."""
        for cat, btn in self._botones_tipo.items():
            if self._tipo_group.id(btn) == id_boton and btn.isChecked():
                self._categoria = cat
                self.setWindowTitle(f"Nuevo Producto - {self.TIPOS[cat]}")
                return

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
            categoria=self._categoria,
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
            "categoria": self._categoria,
            "costo_unitario": Decimal(self.precio_input.text() or "0"),
            "stock_inicial": Decimal(self.cantidad_input.text() or "0"),
            "stock_kg": Decimal(self.stock_kg_input.text() or "0"),
            "stock_minimo": Decimal(self.minimo_input.text() or "0"),
            "unidad_medida": self.unidad_combo.currentText(),
        }


# Alias por compatibilidad con la API anterior (solo abre Materia Prima por defecto).
_CrearProductoMPDialog = _CrearProductoDialog