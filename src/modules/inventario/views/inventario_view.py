"""Inventory dashboard: KPIs, raw materials, finished tires, and configuration."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import cast

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.clientes.services.cliente_service import ClienteService
from src.modules.inventario.models.producto_model import Producto
from src.modules.inventario.services.documento_service import DocumentoService
from src.modules.inventario.services.inventario_config_service import (
    InventarioConfigService,
)
from src.modules.inventario.services.inventario_kpi_service import (
    InventarioKpiService,
)
from src.modules.inventario.services.precio_producto_service import PrecioProductoService
from src.modules.inventario.services.producto_service import ProductoService
from src.modules.llantas.services.llanta_service import LlantaService

# ── Colors ──────────────────────────────────────────────────────────
C_AZUL = "#3498db"
C_AZUL_OSCURO = "#2980b9"
C_VERDE = "#27ae60"
C_AMBAR = "#f39c12"
C_ROJO = "#e74c3c"
C_BG_CARD = "#f8f9fa"

KPI_COLORS = {
    "mp": C_AZUL,
    "valor": C_AZUL,
    "capacidad": C_VERDE,
    "planta": C_AMBAR,
    "margen": C_AMBAR,
}

ANTIGUEDAD_COLORS = {
    30: QColor("#fff3cd"),    # 1 mes: amarillo
    90: QColor("#ffe0b2"),    # 3 meses: naranja claro
    180: QColor("#ffccbc"),   # 6 meses: naranja intenso
    365: QColor("#ffcdd2"),   # 12 meses: rojo claro
}


def _color_antiguedad(dias: int) -> QColor | None:
    if dias >= 365:
        return QColor("#e57373")  # rojo intenso
    if dias >= 180:
        return QColor("#ffccbc")
    if dias >= 90:
        return QColor("#ffe0b2")
    if dias >= 30:
        return QColor("#fff3cd")
    return None


# ═════════════════════════════════════════════════════════════════════
#  KPI Card Widget
# ═════════════════════════════════════════════════════════════════════

class _KpiCard(QFrame):
    """Single KPI metric card."""

    def __init__(self, titulo: str, valor: str, color: str, tooltip: str = "") -> None:
        super().__init__()
        self.setStyleSheet(
            f"""
            _KpiCard {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                border-top: 4px solid {color};
            }}
            """
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)

        self._valor_label = QLabel(valor)
        self._valor_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {color};"
        )
        layout.addWidget(self._valor_label)

        self._titulo_label = QLabel(titulo)
        self._titulo_label.setStyleSheet(
            "font-size: 11px; color: #777; font-weight: 600;"
        )
        layout.addWidget(self._titulo_label)

        self.setLayout(layout)
        self.setMinimumWidth(150)
        if tooltip:
            self.setToolTip(tooltip)

    def actualizar(self, valor: str) -> None:
        self._valor_label.setText(valor)


# ═════════════════════════════════════════════════════════════════════
#  Configuration Dialog
# ═════════════════════════════════════════════════════════════════════

class _CrudTableWidget(QWidget):
    """Generic CRUD table with add/edit/delete."""

    def __init__(
        self,
        columnas: list[str],
        ancho_cols: list[int] | None = None,
    ) -> None:
        super().__init__()
        self._columnas = columnas
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(columnas))
        self.table.setHorizontalHeaderLabels(columnas)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        if ancho_cols:
            for i, w in enumerate(ancho_cols):
                self.table.setColumnWidth(i, w)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ Agregar")
        self.btn_add.setStyleSheet(
            f"QPushButton {{ background: {C_VERDE}; color: white; padding: 6px 16px; "
            "border-radius: 4px; font-weight: bold; }}"
        )
        self.btn_edit = QPushButton("Editar")
        self.btn_edit.setStyleSheet(
            f"QPushButton {{ background: {C_AZUL}; color: white; padding: 6px 16px; "
            "border-radius: 4px; font-weight: bold; }}"
        )
        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setStyleSheet(
            f"QPushButton {{ background: {C_ROJO}; color: white; padding: 6px 16px; "
            "border-radius: 4px; font-weight: bold; }}"
        )
        self.btn_import = QPushButton("📥 Importar Excel")
        self.btn_import.setStyleSheet(
            "QPushButton { background: #6c757d; color: white; padding: 6px 16px; "
            "border-radius: 4px; font-weight: bold; }"
        )
        self.btn_import.setVisible(False)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_import)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def limpiar(self) -> None:
        self.table.setRowCount(0)

    def agregar_fila(self, valores: list[str], datos_id: int) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, val in enumerate(valores):
            item = QTableWidgetItem(val)
            if col == 0:
                item.setData(Qt.ItemDataRole.UserRole, datos_id)
            self.table.setItem(row, col, item)

    def fila_seleccionada(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None


class ConfiguracionInventarioDialog(QDialog):
    """Configuration dialog for precios de producto and precios por cliente."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Precios y Configuración")
        self.resize(900, 600)
        layout = QVBoxLayout()

        self.tabs = QTabWidget()
        self.tab_precios_producto = _CrudTableWidget(
            ["ID", "Diseño", "Dimensión", "Costo Fabr. $", "Precio Mínimo $",
             "Precio Medio $", "Precio Normal $"],
            ancho_cols=[40, 130, 130, 100, 100, 100, 100],
        )
        self.tab_precios_cliente = _CrudTableWidget(
            ["ID", "Cliente", "Diseño", "Dimensión", "Precio Venta $"],
            ancho_cols=[40, 180, 120, 120, 120],
        )

        self.tabs.addTab(self.tab_precios_producto, "Precios de Producto")
        self.tabs.addTab(self.tab_precios_cliente, "Precios por Cliente")
        layout.addWidget(self.tabs)

        # Connect buttons — precios producto
        self.tab_precios_producto.btn_add.clicked.connect(self._add_precio_producto)
        self.tab_precios_producto.btn_edit.clicked.connect(self._edit_precio_producto)
        self.tab_precios_producto.btn_delete.clicked.connect(self._delete_precio_producto)
        self.tab_precios_producto.btn_import.setVisible(True)
        self.tab_precios_producto.btn_import.clicked.connect(self._importar_precios_excel)

        # Connect buttons — precios cliente
        self.tab_precios_cliente.btn_add.clicked.connect(self._add_precio_cliente)
        self.tab_precios_cliente.btn_edit.clicked.connect(self._edit_precio_cliente)
        self.tab_precios_cliente.btn_delete.clicked.connect(self._delete_precio_cliente)

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)
        self._cargar_todo()

    def _cargar_todo(self) -> None:
        self._cargar_precios_producto()
        self._cargar_precios_cliente()

    # ── Precios de Producto ─────────────────────────────────────────

    def _cargar_precios_producto(self) -> None:
        self.tab_precios_producto.limpiar()
        for p in PrecioProductoService.listar():
            diseno = p.diseno.nombre if p.diseno else f"#{p.diseno_id}"
            dimension = p.dimension.display if p.dimension else f"#{p.dimension_id}"
            self.tab_precios_producto.agregar_fila(
                [
                    str(p.id), diseno, dimension,
                    f"${p.costo_fabricacion:,.2f}",
                    f"${p.precio_minimo:,.2f}",
                    f"${p.precio_medio:,.2f}",
                    f"${p.precio_normal:,.2f}",
                ],
                p.id,
            )

    def _add_precio_producto(self) -> None:
        dlg = _PrecioProductoFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar_precios_producto()

    def _edit_precio_producto(self) -> None:
        pk = self.tab_precios_producto.fila_seleccionada()
        if pk is None:
            QMessageBox.information(self, "Seleccionar", "Seleccione un precio")
            return
        dlg = _PrecioProductoFormDialog(self, precio_id=pk)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar_precios_producto()

    def _delete_precio_producto(self) -> None:
        pk = self.tab_precios_producto.fila_seleccionada()
        if pk is None:
            QMessageBox.information(self, "Seleccionar", "Seleccione un precio")
            return
        if QMessageBox.question(self, "Confirmar", "¿Eliminar este precio?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) != QMessageBox.StandardButton.Yes:
            return
        PrecioProductoService.eliminar(pk)
        self._cargar_precios_producto()

    # ── Precios por Cliente ─────────────────────────────────────────

    def _cargar_precios_cliente(self) -> None:
        self.tab_precios_cliente.limpiar()
        for p in InventarioConfigService.listar_precios():
            cliente = p.cliente.nombre if p.cliente else f"#{p.cliente_id}"
            diseno = p.diseno.nombre if p.diseno else f"#{p.diseno_id}"
            dimension = p.dimension.display if p.dimension else f"#{p.dimension_id}"
            self.tab_precios_cliente.agregar_fila(
                [str(p.id), cliente, diseno, dimension, f"${p.precio_venta:,.2f}"],
                p.id,
            )

    def _add_precio_cliente(self) -> None:
        dlg = _PrecioClienteFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar_precios_cliente()

    def _edit_precio_cliente(self) -> None:
        pk = self.tab_precios_cliente.fila_seleccionada()
        if pk is None:
            QMessageBox.information(self, "Seleccionar", "Seleccione un precio")
            return
        dlg = _PrecioClienteFormDialog(self, precio_id=pk)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar_precios_cliente()

    def _delete_precio_cliente(self) -> None:
        pk = self.tab_precios_cliente.fila_seleccionada()
        if pk is None:
            QMessageBox.information(self, "Seleccionar", "Seleccione un precio")
            return
        if QMessageBox.question(
            self, "Confirmar", "¿Eliminar este precio?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        InventarioConfigService.eliminar_precio(pk)
        self._cargar_precios_cliente()

    # ── Excel Import ──────────────────────────────────────────────────

    def _importar_precios_excel(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Importar precios desde Excel", "",
            "Archivos Excel (*.xlsx *.xls);;Todos (*.*)",
        )
        if not ruta:
            return
        ok, msg = PrecioProductoService.importar_desde_excel(ruta)
        if ok:
            QMessageBox.information(self, "Importación completada", msg)
            self._cargar_precios_producto()
        else:
            QMessageBox.warning(self, "Error de importación", msg)


# ── Form dialogs for config ─────────────────────────────────────────

class _PrecioProductoFormDialog(QDialog):
    """Form for editing a master price entry (costo + 3 pricing tiers per design+dimension)."""

    def __init__(self, parent: QWidget | None = None, precio_id: int | None = None) -> None:
        super().__init__(parent)
        self._precio_id = precio_id
        self.setWindowTitle("Editar Precio de Producto" if precio_id else "Nuevo Precio de Producto")
        self.resize(350, 300)
        layout = QFormLayout()

        self.diseno_combo = QComboBox()
        self.dimension_combo = QComboBox()
        self.costo_input = QLineEdit("0")
        self.minimo_input = QLineEdit("0")
        self.medio_input = QLineEdit("0")
        self.normal_input = QLineEdit("0")

        self._cargar_catalogos()
        layout.addRow("Diseño:", self.diseno_combo)
        layout.addRow("Dimensión:", self.dimension_combo)
        layout.addRow("Costo Fabricación $:", self.costo_input)
        layout.addRow("Precio Mínimo $:", self.minimo_input)
        layout.addRow("Precio Medio $:", self.medio_input)
        layout.addRow("Precio Normal $:", self.normal_input)

        if precio_id:
            precios = PrecioProductoService.listar()
            p = next((x for x in precios if x.id == precio_id), None)
            if p:
                idx_d = self.diseno_combo.findData(p.diseno_id)
                if idx_d >= 0:
                    self.diseno_combo.setCurrentIndex(idx_d)
                idx_m = self.dimension_combo.findData(p.dimension_id)
                if idx_m >= 0:
                    self.dimension_combo.setCurrentIndex(idx_m)
                self.costo_input.setText(str(p.costo_fabricacion))
                self.minimo_input.setText(str(p.precio_minimo))
                self.medio_input.setText(str(p.precio_medio))
                self.normal_input.setText(str(p.precio_normal))

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._guardar)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)
        self.setLayout(layout)

    def _cargar_catalogos(self) -> None:
        self.diseno_combo.clear()
        self.dimension_combo.clear()
        for d in LlantaService.listar_disenos():
            self.diseno_combo.addItem(d.nombre, d.id)
        for m in LlantaService.listar_dimensiones():
            self.dimension_combo.addItem(m.display, m.id)

    def _guardar(self) -> None:
        try:
            costo = Decimal(self.costo_input.text() or "0")
            minimo = Decimal(self.minimo_input.text() or "0")
            medio = Decimal(self.medio_input.text() or "0")
            normal = Decimal(self.normal_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Error", "Valor numérico inválido")
            return
        diseno_id = self.diseno_combo.currentData()
        dimension_id = self.dimension_combo.currentData()
        if not diseno_id or not dimension_id:
            QMessageBox.warning(self, "Error", "Seleccione diseño y dimensión")
            return
        PrecioProductoService.guardar(diseno_id, dimension_id, costo, minimo, medio, normal)
        self.accept()


class _PrecioClienteFormDialog(QDialog):
    """Form for editing a per-client price override."""

    def __init__(self, parent: QWidget | None = None, precio_id: int | None = None) -> None:
        super().__init__(parent)
        self._precio_id = precio_id
        self.setWindowTitle("Editar Precio por Cliente" if precio_id else "Nuevo Precio por Cliente")
        self.resize(400, 250)
        layout = QFormLayout()

        self.cliente_combo = QComboBox()
        self.diseno_combo = QComboBox()
        self.dimension_combo = QComboBox()
        self.precio_input = QLineEdit()
        self.precio_input.setPlaceholderText("0.00")

        self._cargar_catalogos()
        layout.addRow("Cliente:", self.cliente_combo)
        layout.addRow("Diseño:", self.diseno_combo)
        layout.addRow("Dimensión:", self.dimension_combo)
        layout.addRow("Precio Venta $:", self.precio_input)

        if precio_id:
            precios = InventarioConfigService.listar_precios()
            p = next((x for x in precios if x.id == precio_id), None)
            if p:
                idx_c = self.cliente_combo.findData(p.cliente_id)
                if idx_c >= 0:
                    self.cliente_combo.setCurrentIndex(idx_c)
                idx_d = self.diseno_combo.findData(p.diseno_id)
                if idx_d >= 0:
                    self.diseno_combo.setCurrentIndex(idx_d)
                idx_m = self.dimension_combo.findData(p.dimension_id)
                if idx_m >= 0:
                    self.dimension_combo.setCurrentIndex(idx_m)
                self.precio_input.setText(str(p.precio_venta))

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._guardar)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)
        self.setLayout(layout)

    def _cargar_catalogos(self) -> None:
        self.cliente_combo.clear()
        self.diseno_combo.clear()
        self.dimension_combo.clear()
        for c in ClienteService.listar_clientes():
            self.cliente_combo.addItem(f"{c.nombre} ({c.nit})", c.id)
        for d in LlantaService.listar_disenos():
            self.diseno_combo.addItem(d.nombre, d.id)
        for m in LlantaService.listar_dimensiones():
            self.dimension_combo.addItem(m.display, m.id)

    def _guardar(self) -> None:
        try:
            precio = Decimal(self.precio_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Error", "Precio inválido")
            return
        cid = self.cliente_combo.currentData()
        did = self.diseno_combo.currentData()
        dim = self.dimension_combo.currentData()
        if not cid or not did or not dim:
            QMessageBox.warning(self, "Error", "Seleccione cliente, diseño y dimensión")
            return
        InventarioConfigService.guardar_precio(cid, did, dim, precio)
        self.accept()


# ═════════════════════════════════════════════════════════════════════
#  Quick-create dialog for raw material products
# ═════════════════════════════════════════════════════════════════════

class _CrearProductoMPDialog(QDialog):
    """Rápido formulario para crear productos de materia prima desde inventario."""

    UNIDADES = ["UNIDAD", "KG", "LT", "CAJA", "PAQ"]

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
        layout.addRow("Precio Unit. $:", self.precio_input)

        self.cantidad_input = QLineEdit()
        self.cantidad_input.setPlaceholderText("0")
        layout.addRow("Cantidad inicial:", self.cantidad_input)

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
            "stock_minimo": Decimal(self.minimo_input.text() or "0"),
            "unidad_medida": self.unidad_combo.currentText(),
        }


# ═════════════════════════════════════════════════════════════════════
#  Document-based movement dialogs (COMPRA / PRODUCCION)
# ═════════════════════════════════════════════════════════════════════

class _LineaProductoDialog(QDialog):
    """Agrega un producto a un documento de movimiento."""

    def __init__(
        self,
        productos: list[Producto],
        tipo: str,  # "ENTRADA" or "SALIDA"
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Agregar Producto")
        self.resize(380, 200)
        layout = QFormLayout()

        self.producto_combo = QComboBox()
        for p in productos:
            stock_str = f" (stock: {p.stock})" if tipo == "SALIDA" else ""
            self.producto_combo.addItem(
                f"{p.nombre} ({p.sku}){stock_str}", p.id
            )
        layout.addRow("Producto:", self.producto_combo)

        self.cantidad_input = QLineEdit()
        self.cantidad_input.setPlaceholderText("0")
        layout.addRow("Cantidad *:", self.cantidad_input)

        self.costo_input = QLineEdit()
        self.costo_input.setPlaceholderText("Dejar vacío = costo actual")
        layout.addRow("Costo Unit.:", self.costo_input)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._validar)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

        self.setLayout(layout)

    def _validar(self) -> None:
        text = self.cantidad_input.text().strip()
        if not text:
            QMessageBox.warning(self, "Validación", "Ingrese la cantidad")
            return
        try:
            cant = Decimal(text)
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad inválida")
            return
        if cant <= 0:
            QMessageBox.warning(self, "Validación", "La cantidad debe ser > 0")
            return
        self.accept()

    def get_data(self) -> tuple[int, Decimal, Decimal | None]:
        pid = self.producto_combo.currentData()
        cantidad = Decimal(self.cantidad_input.text().strip() or "0")
        costo_text = self.costo_input.text().strip()
        costo = Decimal(costo_text) if costo_text else None
        return pid, cantidad, costo


# ═════════════════════════════════════════════════════════════════════
#  Document search / viewer dialog
# ═════════════════════════════════════════════════════════════════════

class _DocumentoSearchDialog(QDialog):
    """Search and view inventory documents."""

    COLUMNAS = ["Documento", "Tipo", "Fecha", "Movimientos", "Observaciones"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Búsqueda de Documentos")
        self.resize(750, 500)
        layout = QVBoxLayout()

        # ── Filters ──────────────────────────────────────────────────
        filter_group = QFrame()
        filter_group.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 6px; padding: 6px; }")
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(8, 6, 8, 6)

        self.filtro_numero = QLineEdit()
        self.filtro_numero.setPlaceholderText("N° documento...")
        self.filtro_numero.setStyleSheet("max-width: 180px;")
        filter_layout.addWidget(QLabel("Número:"))
        filter_layout.addWidget(self.filtro_numero)

        self.filtro_tipo = QComboBox()
        self.filtro_tipo.addItems(["TODOS", "COMPRA", "PRODUCCION"])
        filter_layout.addWidget(QLabel("Tipo:"))
        filter_layout.addWidget(self.filtro_tipo)

        self.filtro_desde = QDateEdit()
        self.filtro_desde.setCalendarPopup(True)
        self.filtro_desde.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(QLabel("Desde:"))
        filter_layout.addWidget(self.filtro_desde)

        self.filtro_hasta = QDateEdit()
        self.filtro_hasta.setCalendarPopup(True)
        self.filtro_hasta.setDate(QDate.currentDate())
        filter_layout.addWidget(QLabel("Hasta:"))
        filter_layout.addWidget(self.filtro_hasta)

        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.clicked.connect(self._buscar)
        btn_buscar.setStyleSheet(
            f"QPushButton {{ background: {C_AZUL}; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; border: none; }}"
        )
        filter_layout.addWidget(btn_buscar)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # ── Results table ────────────────────────────────────────────
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.itemDoubleClicked.connect(self._ver_detalle)
        layout.addWidget(self.tabla)

        # ── Bottom ──────────────────────────────────────────────────
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

        self.setLayout(layout)

        # Load initial results
        self._buscar()

    def _buscar(self) -> None:
        numero = self.filtro_numero.text().strip() or None
        tipo_text = self.filtro_tipo.currentText()
        tipo = tipo_text if tipo_text != "TODOS" else None
        desde = cast(datetime, self.filtro_desde.date().toPython())
        hasta = cast(datetime, self.filtro_hasta.date().toPython())

        docs = DocumentoService.buscar_documentos(
            numero=numero,
            tipo=tipo,
            fecha_desde=desde,
            fecha_hasta=hasta,
        )
        self.tabla.setRowCount(len(docs))
        for row, d in enumerate(docs):
            self.tabla.setItem(row, 0, QTableWidgetItem(d.numero_documento))
            self.tabla.setItem(row, 1, QTableWidgetItem(d.tipo))
            self.tabla.setItem(row, 2, QTableWidgetItem(d.fecha.isoformat()))
            mov_count = len(d.movimientos) if d.movimientos else 0
            self.tabla.setItem(row, 3, QTableWidgetItem(str(mov_count)))
            self.tabla.setItem(row, 4, QTableWidgetItem(d.observaciones or ""))
            # Store id in first column user role
            self.tabla.item(row, 0).setData(Qt.ItemDataRole.UserRole, d.id)

    def _ver_detalle(self) -> None:
        row = self.tabla.currentRow()
        if row < 0:
            return
        doc_id = self.tabla.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not doc_id:
            return
        dlg = _DocumentoDetalleDialog(doc_id, self)
        dlg.exec()


class _DocumentoDetalleDialog(QDialog):
    """Shows the line items of a single document."""

    COLUMNAS = ["Producto", "SKU", "Tipo", "Cantidad", "Costo Unit.", "Total", "Fecha"]

    def __init__(self, documento_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        doc = DocumentoService.obtener_documento(documento_id)
        if not doc:
            QMessageBox.warning(self, "Error", "Documento no encontrado")
            self.reject()
            return

        self.setWindowTitle(f"Documento: {doc.numero_documento}")
        self.resize(650, 400)
        layout = QVBoxLayout()

        # Header info
        info = QLabel(
            f"<b>Documento:</b> {doc.numero_documento}   |   "
            f"<b>Tipo:</b> {doc.tipo}   |   "
            f"<b>Fecha:</b> {doc.fecha.isoformat()}"
        )
        info.setStyleSheet("font-size: 13px; padding: 8px; background: #f8f9fa; border-radius: 6px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Movements table
        movs = DocumentoService.obtener_movimientos_por_documento(documento_id)
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)

        self.tabla.setRowCount(len(movs))
        for row, m in enumerate(movs):
            producto = m.producto
            total = float(m.cantidad) * float(m.costo_unitario)
            self.tabla.setItem(row, 0, QTableWidgetItem(producto.nombre if producto else f"#{m.producto_id}"))
            self.tabla.setItem(row, 1, QTableWidgetItem(producto.sku if producto else ""))
            self.tabla.setItem(row, 2, QTableWidgetItem(m.tipo))
            self.tabla.setItem(row, 3, QTableWidgetItem(str(m.cantidad)))
            self.tabla.setItem(row, 4, QTableWidgetItem(f"${float(m.costo_unitario):,.2f}"))
            self.tabla.setItem(row, 5, QTableWidgetItem(f"${total:,.2f}"))
            self.tabla.setItem(row, 6, QTableWidgetItem(m.fecha.strftime("%d/%m/%Y %H:%M") if m.fecha else ""))

        layout.addWidget(self.tabla)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

        self.setLayout(layout)


# ═════════════════════════════════════════════════════════════════════
#  Main Inventory View
# ═════════════════════════════════════════════════════════════════════

class InventarioView(QWidget):
    """Inventory dashboard with KPIs, raw materials, and finished tires."""

    COLUMNAS_MP = [
        "ID", "SKU", "Nombre", "Categoría", "Unidad", "Stock",
        "Mínimo", "Costo Unit.", "Valor Total",
    ]
    COLUMNAS_TERMINADAS = [
        "ID", "Tiquete", "Diseño", "Dimensión", "Costo Fabr.",
        "Precio Vta.", "Margen", "Cliente", "Días en Planta",
    ]

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout()

        # Header
        header = QLabel("📦 Inventario")
        header.setStyleSheet(
            "font-size: 20px; font-weight: bold; padding: 8px 0;"
        )
        layout.addWidget(header)

        # KPI cards
        kpi_row = QHBoxLayout()
        self._kpi_widgets: dict[str, _KpiCard] = {}
        kpi_defs = [
            ("mp", "MP Disponible", "0", C_AZUL, "Cantidad total de materia prima en stock"),
            ("valor", "Valor Inventario", "$0", C_AZUL, "Valor total del inventario de MP"),
            ("capacidad", "Capacidad Prod.", "0 und", C_VERDE,
             "Llantas estimadas producibles con MP actual"),
            ("planta", "En Planta", "0 und", C_AMBAR,
             "Llantas terminadas sin retirar"),
            ("margen", "Margen Potencial", "$0", C_AMBAR,
             "Margen bruto si se venden todas las llantas en planta"),
        ]
        for key, titulo, valor, color, tooltip in kpi_defs:
            card = _KpiCard(titulo, valor, color, tooltip)
            self._kpi_widgets[key] = card
            kpi_row.addWidget(card)
        layout.addLayout(kpi_row)

        # ── Toolbar ─────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        btn_nuevo_mp = QPushButton("🧾 Nuevo Producto")
        btn_nuevo_mp.setStyleSheet(
            f"QPushButton {{ background: {C_AZUL}; color: white; font-weight: bold; "
            "padding: 8px 18px; border-radius: 5px; border: none; }}"
        )
        btn_nuevo_mp.clicked.connect(self._nuevo_producto_mp)

        btn_docs = QPushButton("📋 Historial MP")
        btn_docs.setStyleSheet(
            "QPushButton { background: #6c757d; color: white; font-weight: bold; "
            "padding: 8px 18px; border-radius: 5px; border: none; }"
        )
        btn_docs.clicked.connect(self._abrir_documentos)

        btn_config = QPushButton("⚙️ Precios y Config")
        btn_config.setStyleSheet(
            "QPushButton { background: #6c757d; color: white; font-weight: bold; "
            "padding: 8px 18px; border-radius: 5px; border: none; }"
        )
        btn_config.clicked.connect(self._abrir_config)

        self.btn_reportes = QPushButton("📊 Reportes ▾")
        self.btn_reportes.setStyleSheet(
            "QPushButton { background: #495057; color: white; font-weight: bold; "
            "padding: 8px 18px; border-radius: 5px; border: none; }"
        )
        self._menu_reportes = QMenu()
        self._menu_reportes.addAction("Reencauchadas esta semana", self._reporte_semanal)
        self._menu_reportes.addAction("1 mes en planta (≥30 días)", self._reporte_1mes)
        self._menu_reportes.addAction("3 meses en planta (≥90 días)", self._reporte_3meses)
        self._menu_reportes.addAction("6 meses en planta (≥180 días)", self._reporte_6meses)
        self._menu_reportes.addAction("12 meses en planta (≥365 días)", self._reporte_12meses)
        self._menu_reportes.addSeparator()
        self._menu_reportes.addAction("📄 MP — Stock general", self._reporte_mp_stock)
        self._menu_reportes.addAction("📄 MP — Punto de reorden (bajo mínimo)", self._reporte_mp_reorden)
        self._menu_reportes.addSeparator()
        self._menu_reportes.addAction("Exportar tabla a Excel (simulado)", self._exportar_excel)
        self.btn_reportes.setMenu(self._menu_reportes)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setStyleSheet(
            "QPushButton { font-size: 16px; padding: 8px 14px; border-radius: 5px; "
            "border: 1px solid #ccc; }"
        )
        btn_refresh.clicked.connect(self._refresh_all)

        toolbar.addWidget(btn_nuevo_mp)
        toolbar.addWidget(btn_docs)
        toolbar.addStretch()
        toolbar.addWidget(btn_config)
        toolbar.addWidget(self.btn_reportes)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        # ── Tabs ────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #ddd; border-top: none; }"
        )

        # Tab 1: Materia Prima
        self.tab_mp = QWidget()
        mp_layout = QVBoxLayout()
        mp_layout.setContentsMargins(0, 0, 0, 0)

        mp_filter_row = QHBoxLayout()
        self.mp_busqueda = QLineEdit()
        self.mp_busqueda.setPlaceholderText("Buscar por nombre, SKU...")
        self.mp_busqueda.setStyleSheet("font-size: 13px; padding: 5px; max-width: 300px;")
        self.mp_busqueda.textChanged.connect(self._filtrar_mp)
        mp_filter_row.addWidget(self.mp_busqueda)
        mp_filter_row.addStretch()
        mp_layout.addLayout(mp_filter_row)

        self.tabla_mp = QTableWidget()
        self.tabla_mp.setColumnCount(len(self.COLUMNAS_MP))
        self.tabla_mp.setHorizontalHeaderLabels(self.COLUMNAS_MP)
        self.tabla_mp.horizontalHeader().setStretchLastSection(True)
        self.tabla_mp.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_mp.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_mp.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_mp.setAlternatingRowColors(True)
        self.tabla_mp.setColumnHidden(0, True)
        mp_layout.addWidget(self.tabla_mp)
        self.tab_mp.setLayout(mp_layout)
        self.tabs.addTab(self.tab_mp, "Materia Prima")

        # Tab 2: Llantas Terminadas
        self.tab_term = QWidget()
        term_layout = QVBoxLayout()
        term_layout.setContentsMargins(0, 0, 0, 0)

        self.term_busqueda = QLineEdit()
        self.term_busqueda.setPlaceholderText("Buscar por código, cliente...")
        self.term_busqueda.setStyleSheet("font-size: 13px; padding: 5px; max-width: 300px;")
        self.term_busqueda.textChanged.connect(self._filtrar_terminadas)
        term_layout.addWidget(self.term_busqueda)

        self.tabla_term = QTableWidget()
        self.tabla_term.setColumnCount(len(self.COLUMNAS_TERMINADAS))
        self.tabla_term.setHorizontalHeaderLabels(self.COLUMNAS_TERMINADAS)
        self.tabla_term.horizontalHeader().setStretchLastSection(True)
        self.tabla_term.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_term.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_term.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_term.setAlternatingRowColors(True)
        self.tabla_term.setColumnHidden(0, True)
        term_layout.addWidget(self.tabla_term)
        self.tab_term.setLayout(term_layout)
        self.tabs.addTab(self.tab_term, "Llantas Terminadas")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # Data cache
        self._mp_cache: list[Producto] = []
        self._term_cache: list[dict] = []

        # Initial load
        QTimer.singleShot(0, self._refresh_all)

    # ── Refresh ─────────────────────────────────────────────────────

    def _refresh_all(self) -> None:
        try:
            self._cargar_kpis()
        except Exception as e:
            print(f"[InventarioView] Error cargando KPIs: {e}")
        try:
            self._cargar_mp()
        except Exception as e:
            print(f"[InventarioView] Error cargando MP: {e}")
        try:
            self._cargar_terminadas()
        except Exception as e:
            print(f"[InventarioView] Error cargando terminadas: {e}")

    def _cargar_kpis(self) -> None:
        kpis = InventarioKpiService.resumen_kpis()
        self._kpi_widgets["mp"].actualizar(str(kpis["mp_disponible"]))
        self._kpi_widgets["valor"].actualizar(f"${kpis['valor_inventario']:,.0f}")
        self._kpi_widgets["capacidad"].actualizar(f"{kpis['capacidad_prod']} und")
        self._kpi_widgets["planta"].actualizar(f"{kpis['llantas_en_planta']} und")
        self._kpi_widgets["margen"].actualizar(f"${kpis['margen_potencial']:,.0f}")

    # ── Materia Prima ───────────────────────────────────────────────

    def _cargar_mp(self) -> None:
        self._mp_cache = InventarioKpiService.materias_primas()
        self._poblar_tabla_mp(self._mp_cache)

    def _poblar_tabla_mp(self, productos: list[Producto]) -> None:
        self.tabla_mp.setRowCount(len(productos))
        for row, p in enumerate(productos):
            stock = float(p.stock or 0)
            minimo = float(p.stock_minimo or 0)
            costo = float(p.costo_unitario or 0)
            valor = stock * costo
            self.tabla_mp.setItem(row, 0, QTableWidgetItem(str(p.id)))           # ID (hidden)
            self.tabla_mp.setItem(row, 1, QTableWidgetItem(p.sku or ""))          # SKU
            self.tabla_mp.setItem(row, 2, QTableWidgetItem(p.nombre or ""))       # Nombre
            self.tabla_mp.setItem(row, 3, QTableWidgetItem(p.categoria or ""))    # Categoría
            self.tabla_mp.setItem(row, 4, QTableWidgetItem(p.unidad_medida or ""))# Unidad
            self.tabla_mp.setItem(row, 5, QTableWidgetItem(str(stock)))           # Stock
            self.tabla_mp.setItem(row, 6, QTableWidgetItem(str(minimo)))          # Mínimo
            self.tabla_mp.setItem(
                row, 7, QTableWidgetItem(f"${costo:,.2f}")                       # Costo Unit.
            )
            self.tabla_mp.setItem(
                row, 8, QTableWidgetItem(f"${valor:,.2f}")                       # Valor Total
            )

    def _filtrar_mp(self) -> None:
        term = self.mp_busqueda.text().strip().lower()
        if not term:
            self._poblar_tabla_mp(self._mp_cache)
            return
        filtrados = [
            p for p in self._mp_cache
            if term in (p.nombre or "").lower()
            or term in (p.sku or "").lower()
        ]
        self._poblar_tabla_mp(filtrados)

    # ── Llantas Terminadas ──────────────────────────────────────────

    def _cargar_terminadas(self) -> None:
        self._term_cache = InventarioKpiService.terminadas_en_planta()
        self._poblar_tabla_term(self._term_cache)

    def _poblar_tabla_term(self, llantas: list[dict]) -> None:
        self.tabla_term.setRowCount(len(llantas))
        for row, ll in enumerate(llantas):
            self.tabla_term.setItem(row, 0, QTableWidgetItem(str(ll["id"])))
            self.tabla_term.setItem(row, 1, QTableWidgetItem(ll["tiquete"]))
            self.tabla_term.setItem(row, 2, QTableWidgetItem(ll["diseno"]))
            self.tabla_term.setItem(row, 3, QTableWidgetItem(ll["dimension"]))
            self.tabla_term.setItem(
                row, 4, QTableWidgetItem(f"${ll['costo_produccion']:,.0f}")
            )
            self.tabla_term.setItem(
                row, 5, QTableWidgetItem(f"${ll['precio_venta']:,.0f}")
            )
            margen = ll["margen"]
            margen_str = f"${margen:,.0f}"
            if margen >= 0:
                margen_str = f"+{margen_str}"
            item_margen = QTableWidgetItem(margen_str)
            item_margen.setForeground(QColor(C_VERDE) if margen >= 0 else QColor(C_ROJO))
            self.tabla_term.setItem(row, 6, item_margen)
            self.tabla_term.setItem(row, 7, QTableWidgetItem(ll["cliente"]))
            self.tabla_term.setItem(
                row, 8, QTableWidgetItem(str(ll["dias_en_planta"]))
            )

            # Color row by aging
            color = _color_antiguedad(ll["dias_en_planta"])
            if color:
                for col in range(self.tabla_term.columnCount()):
                    item = self.tabla_term.item(row, col)
                    if item:
                        item.setBackground(color)

    def _filtrar_terminadas(self) -> None:
        term = self.term_busqueda.text().strip().lower()
        if not term:
            self._poblar_tabla_term(self._term_cache)
            return
        filtrados = [
            ll for ll in self._term_cache
            if term in (ll["tiquete"] or "").lower()
            or term in (ll["cliente"] or "").lower()
        ]
        self._poblar_tabla_term(filtrados)

    # ── Actions ─────────────────────────────────────────────────────

    def _nuevo_producto_mp(self) -> None:
        """Quick-create a raw material product."""
        dlg = _CrearProductoMPDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_all()

    def _abrir_documentos(self) -> None:
        """Open document search dialog."""
        dlg = _DocumentoSearchDialog(self)
        dlg.exec()

    def _abrir_config(self) -> None:
        dlg = ConfiguracionInventarioDialog(self)
        dlg.exec()

    # ── Reports ─────────────────────────────────────────────────────

    def _reporte_semanal(self) -> None:
        hoy = datetime.now()
        inicio = hoy - timedelta(days=7)
        datos = InventarioKpiService.reporte_semanal(inicio, hoy)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte Semanal",
            f"Se encontraron {len(datos)} llantas reencauchadas esta semana."
        )

    def _reporte_1mes(self) -> None:
        datos = InventarioKpiService.reporte_antiguedad(30)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte 1 mes",
            f"{len(datos)} llantas con ≥30 días en planta."
        )

    def _reporte_3meses(self) -> None:
        datos = InventarioKpiService.reporte_antiguedad(90)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte 3 meses",
            f"{len(datos)} llantas con ≥90 días en planta."
        )

    def _reporte_6meses(self) -> None:
        datos = InventarioKpiService.reporte_antiguedad(180)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte 6 meses",
            f"{len(datos)} llantas con ≥180 días en planta."
        )

    def _reporte_12meses(self) -> None:
        datos = InventarioKpiService.reporte_antiguedad(365)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte 12 meses",
            f"{len(datos)} llantas con ≥365 días en planta."
        )

    # ── MP Reports ──────────────────────────────────────────────────

    def _reporte_mp_stock(self) -> None:
        """Show MP stock report in the MP table."""
        self._cargar_mp()
        self.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self, "Stock MP",
            f"Reporte de stock general de materia prima ({len(self._mp_cache)} productos)."
        )

    def _reporte_mp_reorden(self) -> None:
        """Filter MP table to show only products below minimum stock."""
        bajos = [
            p for p in self._mp_cache
            if (p.stock or 0) < (p.stock_minimo or 0)
        ]
        self._poblar_tabla_mp(bajos)
        self.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self, "Punto de Reorden",
            f"{len(bajos)} productos de MP están por debajo del mínimo en planta."
        )

    def _exportar_excel(self) -> None:
        QMessageBox.information(
            self, "Exportar",
            "Exportación a Excel disponible en próxima versión."
        )
