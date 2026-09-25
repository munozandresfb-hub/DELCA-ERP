from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.modules.inventario.models.producto_model import Producto
from src.modules.inventario.services.producto_service import ProductoService


import logging

logger = logging.getLogger("delca.views")
class ProductoFormDialog(QDialog):
    """Dialog for creating or editing a product."""

    def __init__(
        self,
        parent: QWidget | None = None,
        producto: Producto | None = None,
    ) -> None:
        super().__init__(parent)
        self.producto = producto
        self.setWindowTitle(
            "Editar Producto" if producto else "Nuevo Producto"
        )
        self.resize(500, 450)
        self.setup_ui()
        if producto:
            self._cargar_datos(producto)

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        form = QFormLayout()

        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Nombre del producto")
        form.addRow("Nombre *:", self.nombre_input)

        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("SKU único")
        form.addRow("SKU *:", self.sku_input)

        self.categoria_combo = QComboBox()
        self.categoria_combo.setEditable(True)
        self.categoria_combo.addItems(ProductoService.CATEGORIAS)
        form.addRow("Categoría:", self.categoria_combo)

        self.costo_input = QLineEdit()
        self.costo_input.setPlaceholderText("0.00")
        form.addRow("Costo/KG:", self.costo_input)

        self.precio_input = QLineEdit()
        self.precio_input.setPlaceholderText("0.00")
        form.addRow("Precio Venta:", self.precio_input)

        self.unidad_input = QLineEdit()
        self.unidad_input.setPlaceholderText("UNIDAD, KG, LT, etc.")
        self.unidad_input.setText("UNIDAD")
        form.addRow("Unidad Medida:", self.unidad_input)

        self.descripcion_input = QTextEdit()
        self.descripcion_input.setMaximumHeight(80)
        form.addRow("Descripción:", self.descripcion_input)

        # Stock inicial (only for new products)
        if not self.producto:
            self.stock_input = QLineEdit()
            self.stock_input.setPlaceholderText("0")
            form.addRow("Stock Inicial:", self.stock_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        guardar_btn = QPushButton("Guardar")
        guardar_btn.clicked.connect(self._guardar)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addWidget(guardar_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _cargar_datos(self, p: Producto) -> None:
        self.nombre_input.setText(p.nombre or "")
        self.sku_input.setText(p.sku or "")
        idx = self.categoria_combo.findText(p.categoria or "")
        if idx >= 0:
            self.categoria_combo.setCurrentIndex(idx)
        self.costo_input.setText(str(p.costo_unitario) if p.costo_unitario else "")
        self.precio_input.setText(str(p.precio_venta) if p.precio_venta else "")
        self.unidad_input.setText(p.unidad_medida or "UNIDAD")
        self.descripcion_input.setPlainText(p.descripcion or "")

    def _guardar(self) -> None:
        nombre = self.nombre_input.text().strip()
        sku = self.sku_input.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio")
            return
        if not sku:
            QMessageBox.warning(self, "Validación", "El SKU es obligatorio")
            return
        self.accept()

    def get_data(self) -> dict:
        data = {
            "nombre": self.nombre_input.text().strip(),
            "sku": self.sku_input.text().strip(),
            "categoria": self.categoria_combo.currentText() or None,
            "costo_unitario": self._parse_decimal(self.costo_input.text()),
            "precio_venta": self._parse_decimal(self.precio_input.text()),
            "unidad_medida": self.unidad_input.text().strip() or "UNIDAD",
            "descripcion": self.descripcion_input.toPlainText().strip() or None,
        }
        if not self.producto:
            data["stock_inicial"] = self._parse_decimal(
                getattr(self, "stock_input").text()
            )
        return data

    @staticmethod
    def _parse_decimal(text: str) -> Decimal:
        text = text.strip()
        if not text:
            return Decimal("0")
        try:
            return Decimal(text)
        except Exception:
            return Decimal("0")


class MovimientoDialog(QDialog):
    """Dialog for registering an inventory movement."""

    def __init__(
        self, producto: Producto, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.producto = producto
        self.setWindowTitle(f"Movimiento - {producto.nombre}")
        self.resize(400, 300)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        form = QFormLayout()

        info = QLabel(
            f"Producto: {self.producto.nombre}\n"
            f"SKU: {self.producto.sku}\n"
            f"Stock actual: {self.producto.stock}"
        )
        info.setStyleSheet(
            "font-size: 13px; padding: 8px; background: #f8f9fa;"
            "border-radius: 6px;"
        )
        layout.addWidget(info)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(
            ["ENTRADA", "SALIDA", "MERMA", "AJUSTE"]
        )
        form.addRow("Tipo:", self.tipo_combo)

        self.cantidad_input = QLineEdit()
        self.cantidad_input.setPlaceholderText("0")
        form.addRow("Cantidad *:", self.cantidad_input)

        # Cantidad en KG — necesaria para bandas (costo por KG)
        self.kg_input = QLineEdit()
        self.kg_input.setPlaceholderText("0")
        form.addRow("Cantidad KG:", self.kg_input)

        self.costo_input = QLineEdit()
        self.costo_input.setPlaceholderText(
            f"{self.producto.costo_unitario}"
        )
        form.addRow("Costo/KG:", self.costo_input)

        self.referencia_input = QLineEdit()
        self.referencia_input.setPlaceholderText(
            "N° factura, remisión, etc."
        )
        form.addRow("Referencia:", self.referencia_input)

        self.obs_input = QLineEdit()
        form.addRow("Observaciones:", self.obs_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        guardar_btn = QPushButton("Registrar")
        guardar_btn.clicked.connect(self._guardar)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addWidget(guardar_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _guardar(self) -> None:
        cantidad_text = self.cantidad_input.text().strip()
        if not cantidad_text:
            QMessageBox.warning(
                self, "Validación", "Ingrese la cantidad"
            )
            return
        try:
            cantidad = Decimal(cantidad_text)
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad inválida")
            return
        if cantidad <= 0:
            QMessageBox.warning(
                self, "Validación", "La cantidad debe ser mayor a cero"
            )
            return
        self.accept()

    def get_data(self) -> tuple:
        return (
            self.tipo_combo.currentText(),
            self._parse_decimal(self.cantidad_input.text()),
            self._parse_decimal(self.kg_input.text()),
            self._parse_decimal(self.costo_input.text()),
            self.referencia_input.text().strip() or None,
            self.obs_input.text().strip() or None,
        )

    @staticmethod
    def _parse_decimal(text: str) -> Decimal:
        text = text.strip()
        if not text:
            return Decimal("0")
        try:
            return Decimal(text)
        except Exception:
            return Decimal("0")


class ProductosView(QWidget):
    """Product management view with table, search, CRUD, and movements."""

    COLUMNAS = [
        "ID",
        "Nombre",
        "SKU",
        "Categoría",
        "Stock",
        "Costo",
        "Precio",
        "Unidad",
        "Activo",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setup_ui()
        try:
            self._cargar_datos()
        except Exception as e:
            logger.error(f"[ProductosView] Error al cargar datos iniciales", exc_info=True)

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # Header
        header = QLabel("Inventario / Productos")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px 0;"
        )
        layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por nombre, SKU...")
        self.search_input.textChanged.connect(self._buscar)
        toolbar.addWidget(self.search_input)

        toolbar.addStretch()

        nuevo_btn = QPushButton("+ Nuevo Producto")
        nuevo_btn.clicked.connect(self._nuevo_producto)
        toolbar.addWidget(nuevo_btn)

        editar_btn = QPushButton("Editar")
        editar_btn.clicked.connect(self._editar_producto)
        toolbar.addWidget(editar_btn)

        mov_btn = QPushButton("📦 Movimiento")
        mov_btn.clicked.connect(self._registrar_movimiento)
        toolbar.addWidget(mov_btn)

        eliminar_btn = QPushButton("Eliminar")
        eliminar_btn.clicked.connect(self._eliminar_producto)
        toolbar.addWidget(eliminar_btn)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNAS))
        self.table.setHorizontalHeaderLabels(self.COLUMNAS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _cargar_datos(self) -> None:
        productos = ProductoService.listar_productos()
        self._poblar_tabla(productos)

    def _poblar_tabla(self, productos: list[Producto]) -> None:
        self.table.setRowCount(len(productos))

        for row, p in enumerate(productos):
            self.table.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self.table.setItem(row, 1, QTableWidgetItem(p.nombre or ""))
            self.table.setItem(row, 2, QTableWidgetItem(p.sku or ""))
            self.table.setItem(
                row, 3, QTableWidgetItem(p.categoria or "")
            )
            self.table.setItem(
                row, 4, QTableWidgetItem(str(p.stock or 0))
            )
            self.table.setItem(
                row,
                5,
                QTableWidgetItem(
                    f"${p.costo_unitario:,.2f}" if p.costo_unitario else "$0"
                ),
            )
            self.table.setItem(
                row,
                6,
                QTableWidgetItem(
                    f"${p.precio_venta:,.2f}" if p.precio_venta else "$0"
                ),
            )
            self.table.setItem(
                row, 7, QTableWidgetItem(p.unidad_medida or "")
            )
            self.table.setItem(
                row, 8, QTableWidgetItem("Sí" if p.activo else "No")
            )

        self.table.setColumnHidden(0, True)

    def _buscar(self) -> None:
        termino = self.search_input.text()
        if termino:
            productos = ProductoService.buscar(termino)
        else:
            productos = ProductoService.listar_productos()
        self._poblar_tabla(productos)

    def _nuevo_producto(self) -> None:
        dialog = ProductoFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        ok, resultado = ProductoService.crear(**data)

        if ok:
            self._cargar_datos()
            QMessageBox.information(
                self, "Éxito", f"Producto '{data['nombre']}' creado"
            )
        else:
            QMessageBox.warning(self, "Error", str(resultado))

    def _editar_producto(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Seleccionar", "Seleccione un producto de la tabla"
            )
            return

        producto_id = int(self.table.item(row, 0).text())
        producto = ProductoService.obtener_por_id(producto_id)
        if not producto:
            QMessageBox.warning(self, "Error", "Producto no encontrado")
            return

        dialog = ProductoFormDialog(self, producto)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        ok, msg = ProductoService.actualizar(
            producto_id=producto_id, **data
        )

        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _registrar_movimiento(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Seleccionar",
                "Seleccione un producto de la tabla",
            )
            return

        producto_id = int(self.table.item(row, 0).text())
        producto = ProductoService.obtener_por_id(producto_id)
        if not producto:
            QMessageBox.warning(self, "Error", "Producto no encontrado")
            return

        dialog = MovimientoDialog(producto, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        tipo, cantidad, cantidad_kg, costo, ref, obs = dialog.get_data()
        ok, msg = ProductoService.registrar_movimiento(
            producto_id=producto_id,
            tipo=tipo,
            cantidad=cantidad,
            cantidad_kg=cantidad_kg,
            costo_unitario=costo if costo else None,
            referencia=ref,
            observaciones=obs,
        )

        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _eliminar_producto(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Seleccionar", "Seleccione un producto de la tabla"
            )
            return

        producto_id = int(self.table.item(row, 0).text())
        nombre = self.table.item(row, 1).text()

        confirm = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Está seguro de eliminar '{nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, msg = ProductoService.eliminar(producto_id)
        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)
