"""Diálogos de configuración: precios de producto y precios por cliente."""

from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.modules.clientes.services.cliente_service import ClienteService
from src.modules.inventario.services.inventario_config_service import (
    InventarioConfigService,
)
from src.modules.inventario.services.precio_producto_service import PrecioProductoService
from src.modules.inventario.views.inventario_view._widgets import _CrudTableWidget
from src.modules.llantas.services.llanta_service import LlantaService


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