"""Standalone CRUD dialog for PrecioProducto (costo + 3 precios por diseño+dimensión).

Accessible from facturación toolbar. Reuses PrecioProductoService.
"""

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.inventario.services.precio_producto_service import PrecioProductoService
from src.modules.llantas.services.llanta_service import LlantaService


class _PrecioProductoFormDialog(QDialog):
    """Form for creating/editing a single PrecioProducto entry."""

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

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
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


class _CrudTableWidget(QWidget):
    """Generic CRUD table with add/edit/delete/import buttons."""

    C_AZUL = "#3498db"
    C_VERDE = "#27ae60"
    C_ROJO = "#e74c3c"

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
            f"QPushButton {{ background: {self.C_VERDE}; color: white; padding: 6px 16px; "
            f"border-radius: 4px; font-weight: bold; }}"
        )
        self.btn_edit = QPushButton("Editar")
        self.btn_edit.setStyleSheet(
            f"QPushButton {{ background: {self.C_AZUL}; color: white; padding: 6px 16px; "
            f"border-radius: 4px; font-weight: bold; }}"
        )
        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setStyleSheet(
            f"QPushButton {{ background: {self.C_ROJO}; color: white; padding: 6px 16px; "
            f"border-radius: 4px; font-weight: bold; }}"
        )
        self.btn_import = QPushButton("Importar Excel")
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


class PreciosDisenoDialog(QDialog):
    """Standalone CRUD for master price list (PrecioProducto)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Precios de Producto (Diseño + Dimensión)")
        self.resize(850, 500)
        layout = QVBoxLayout()

        header = QLabel("Catálogo de Precios — Costo de Fabricación + 3 Precios por Diseño+Dimensión")
        header.setStyleSheet("font-size: 14px; font-weight: 600; color: #3498db; padding: 6px 0;")
        layout.addWidget(header)

        # ── Filter row ──
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtrar por Diseño:"))
        self.filtro_diseno = QComboBox()
        self.filtro_diseno.addItem("Todos", None)
        for d in LlantaService.listar_disenos():
            self.filtro_diseno.addItem(d.nombre, d.id)
        self.filtro_diseno.currentIndexChanged.connect(self._cargar_datos)
        filter_row.addWidget(self.filtro_diseno)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # ── CRUD table ──
        self.table_widget = _CrudTableWidget(
            ["ID", "Diseño", "Dimensión", "Costo Fabr. $", "Precio Mínimo $",
             "Precio Medio $", "Precio Normal $"],
            ancho_cols=[40, 130, 130, 100, 100, 100, 100],
        )
        self.table_widget.btn_import.setVisible(True)
        self.table_widget.btn_add.clicked.connect(self._add)
        self.table_widget.btn_edit.clicked.connect(self._edit)
        self.table_widget.btn_delete.clicked.connect(self._delete)
        self.table_widget.btn_import.clicked.connect(self._importar_excel)
        layout.addWidget(self.table_widget)

        # Close
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet(
            "QPushButton { background: #3498db; color: white; font-size: 13px; "
            "font-weight: bold; padding: 6px 20px; border-radius: 4px; border: none; }"
            "QPushButton:hover { background: #2980b9; }"
        )
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self._cargar_datos()

    def _cargar_datos(self) -> None:
        self.table_widget.limpiar()
        diseno_id = self.filtro_diseno.currentData()
        for p in PrecioProductoService.listar(diseno_id=diseno_id):
            diseno = p.diseno.nombre if p.diseno else f"#{p.diseno_id}"
            dimension = p.dimension.display if p.dimension else f"#{p.dimension_id}"
            self.table_widget.agregar_fila(
                [
                    str(p.id), diseno, dimension,
                    f"${p.costo_fabricacion:,.2f}",
                    f"${p.precio_minimo:,.2f}",
                    f"${p.precio_medio:,.2f}",
                    f"${p.precio_normal:,.2f}",
                ],
                p.id,
            )

    def _add(self) -> None:
        dlg = _PrecioProductoFormDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar_datos()

    def _edit(self) -> None:
        pk = self.table_widget.fila_seleccionada()
        if pk is None:
            QMessageBox.information(self, "Seleccionar", "Seleccione un precio")
            return
        dlg = _PrecioProductoFormDialog(self, precio_id=pk)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar_datos()

    def _delete(self) -> None:
        pk = self.table_widget.fila_seleccionada()
        if pk is None:
            QMessageBox.information(self, "Seleccionar", "Seleccione un precio")
            return
        if QMessageBox.question(
            self, "Confirmar", "¿Eliminar este precio?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        PrecioProductoService.eliminar(pk)
        self._cargar_datos()

    def _importar_excel(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Importar precios desde Excel", "",
            "Archivos Excel (*.xlsx *.xls);;Todos (*.*)",
        )
        if not ruta:
            return
        ok, msg = PrecioProductoService.importar_desde_excel(ruta)
        if ok:
            QMessageBox.information(self, "Importación completada", msg)
            self._cargar_datos()
        else:
            QMessageBox.warning(self, "Error de importación", msg)
