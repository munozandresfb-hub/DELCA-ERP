from decimal import Decimal

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from src.modules.clientes.services.cliente_service import ClienteService
from src.modules.finanzas.models.factura_model import Factura
from src.modules.finanzas.services.factura_service import FacturaService
from src.modules.inventario.views.precios_view import PreciosDisenoDialog
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.services.llanta_service import LlantaService


class FacturaFormDialog(QDialog):
    """Dialog for creating a new invoice from billed tires.

    One or more tires can be added; each line pre-fills its price from the
    tire's ``precio_venta`` (set in "Nueva Llanta") and can be edited. The
    total pre-fills as the sum of line prices but stays manually editable —
    the final total is the amount charged to the client.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nueva Factura")
        self.resize(680, 580)
        self._clientes: list[tuple[int, str]] = []
        self._items: list[dict] = []
        self._llantas_dict: dict[int, Llanta] = {}
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        form = QFormLayout()

        input_style = "font-size: 14px; padding: 6px;"
        label_style = "font-size: 14px; font-weight: 600;"

        # Cliente selector
        self.cliente_combo = QComboBox()
        self.cliente_combo.setStyleSheet(input_style)
        self._cargar_clientes()
        lbl = QLabel("Cliente *:")
        lbl.setStyleSheet(label_style)
        form.addRow(lbl, self.cliente_combo)

        # ── Llantas a facturar ──
        llantas_header = QLabel("Llantas a facturar:")
        llantas_header.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #8e44ad; padding-top: 8px;"
        )
        form.addRow(llantas_header)

        picker_row = QHBoxLayout()
        self.llanta_combo = QComboBox()
        self.llanta_combo.setStyleSheet(input_style)
        self.llanta_combo.setMinimumWidth(340)
        self._cargar_llantas_disponibles()
        picker_row.addWidget(self.llanta_combo, 1)

        add_btn = QPushButton("+ Agregar Llanta")
        add_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; border: none; }"
            "QPushButton:hover { background-color: #219a52; }"
        )
        add_btn.clicked.connect(self._agregar_llanta)
        picker_row.addWidget(add_btn)
        form.addRow(picker_row)

        # Items table: Tiquete | Dimensión | Diseño | Precio | Acción
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(
            ["Tiquete", "Dimensión", "Diseño", "Precio", ""]
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.items_table.setColumnWidth(3, 130)
        self.items_table.setColumnWidth(4, 60)
        self.items_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.items_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setMinimumHeight(140)
        form.addRow(self.items_table)

        self.total_input = QLineEdit()
        self.total_input.setPlaceholderText("0.00")
        self.total_input.setStyleSheet(input_style)
        self.total_input.setToolTip(
            "Total a cobrar al cliente. Se precarga con la suma de los precios "
            "de las llantas; puede editarlo manualmente."
        )
        lbl = QLabel("Total a cobrar *:")
        lbl.setStyleSheet(label_style)
        form.addRow(lbl, self.total_input)

        # Plazo de pago
        self.plazo_spin = QSpinBox()
        self.plazo_spin.setRange(1, 365)
        self.plazo_spin.setValue(30)
        self.plazo_spin.setSuffix(" días")
        self.plazo_spin.setStyleSheet(input_style)
        lbl = QLabel("Plazo de pago:")
        lbl.setStyleSheet(label_style)
        form.addRow(lbl, self.plazo_spin)

        self.observaciones_input = QTextEdit()
        self.observaciones_input.setPlaceholderText("Observaciones (opcional)")
        self.observaciones_input.setMaximumHeight(70)
        lbl = QLabel("Observaciones:")
        lbl.setStyleSheet(label_style)
        form.addRow(lbl, self.observaciones_input)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        guardar_btn = QPushButton("Crear Factura")
        guardar_btn.clicked.connect(self._guardar)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addWidget(guardar_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _cargar_clientes(self) -> None:
        clientes = ClienteService.listar_clientes()
        self._clientes = []
        self.cliente_combo.clear()
        for c in clientes:
            if c.activo:
                label = f"{c.nombre} ({c.nit})"
                self.cliente_combo.addItem(label, c.id)
                self._clientes.append((c.id, label))

    def _cargar_llantas_disponibles(self) -> None:
        """Load tires not yet billed in an active invoice."""
        disponibles = FacturaService.listar_llantas_facturables()
        self._llantas_dict = {l.id: l for l in disponibles}
        self.llanta_combo.clear()
        self.llanta_combo.addItem("-- Seleccionar llanta --", None)
        for l in disponibles:
            marca = l.marca_obj.nombre if l.marca_obj else (l.marca or "")
            dim = l.dimension_obj.display if l.dimension_obj else (l.dimension or "")
            label = f"{l.tiquete} — {marca} {dim}".strip(" —")
            self.llanta_combo.addItem(label, l.id)

    def _agregar_llanta(self) -> None:
        """Add the selected tire as a line item, pre-filling precio_venta."""
        llanta_id = self.llanta_combo.currentData()
        if not llanta_id:
            QMessageBox.warning(self, "Validación", "Seleccione una llanta")
            return
        if any(it["llanta_id"] == llanta_id for it in self._items):
            QMessageBox.warning(self, "Validación", "Esa llanta ya está en la factura")
            return

        llanta = self._llantas_dict.get(llanta_id)
        if not llanta:
            QMessageBox.warning(self, "Error", "Llanta no encontrada")
            return

        precio = float(llanta.precio_venta or 0)
        self._items.append(
            {
                "llanta_id": llanta_id,
                "tiquete": llanta.tiquete or "",
                "dimension": (
                    llanta.dimension_obj.display
                    if llanta.dimension_obj
                    else (llanta.dimension or "—")
                ),
                "diseno": llanta.diseno_obj.nombre if llanta.diseno_obj else "—",
                "precio": precio,
            }
        )
        self._refrescar_tabla_items()

        # Remove added tire from picker
        idx = self.llanta_combo.findData(llanta_id)
        if idx >= 0:
            self.llanta_combo.removeItem(idx)

    def _refrescar_tabla_items(self) -> None:
        self.items_table.setRowCount(len(self._items))
        for row, it in enumerate(self._items):
            self.items_table.setItem(row, 0, QTableWidgetItem(it["tiquete"]))
            self.items_table.setItem(row, 1, QTableWidgetItem(it["dimension"]))
            self.items_table.setItem(row, 2, QTableWidgetItem(it["diseno"]))
            precio_spin = QDoubleSpinBox()
            precio_spin.setRange(0, 9999999)
            precio_spin.setPrefix("$ ")
            precio_spin.setDecimals(2)
            precio_spin.setValue(it["precio"])
            precio_spin.valueChanged.connect(
                lambda value, r=row: self._on_precio_cambiado(r, value)
            )
            self.items_table.setCellWidget(row, 3, precio_spin)
            quitar_btn = QPushButton("✕")
            quitar_btn.setToolTip("Quitar llanta")
            quitar_btn.setStyleSheet(
                "QPushButton { color: #e74c3c; font-weight: bold; border: none; }"
            )
            quitar_btn.clicked.connect(
                lambda _=False, r=row: self._quitar_llanta(r)
            )
            self.items_table.setCellWidget(row, 4, quitar_btn)
        self._recalcular_total()

    def _on_precio_cambiado(self, row: int, value: float) -> None:
        if 0 <= row < len(self._items):
            self._items[row]["precio"] = value
            self._recalcular_total()

    def _quitar_llanta(self, row: int) -> None:
        if 0 <= row < len(self._items):
            item = self._items.pop(row)
            self._refrescar_tabla_items()
            # Re-add tire to picker
            llanta = self._llantas_dict.get(item["llanta_id"])
            if llanta:
                marca = llanta.marca_obj.nombre if llanta.marca_obj else (llanta.marca or "")
                dim = (
                    llanta.dimension_obj.display
                    if llanta.dimension_obj
                    else (llanta.dimension or "")
                )
                label = f"{llanta.tiquete} — {marca} {dim}".strip(" —")
                self.llanta_combo.addItem(label, llanta.id)

    def _recalcular_total(self) -> None:
        total = sum(it["precio"] for it in self._items)
        self.total_input.setText(f"{total:,.2f}")

    def _guardar(self) -> None:
        if self.cliente_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Validación", "Seleccione un cliente")
            return
        if not self._items:
            QMessageBox.warning(
                self, "Validación", "Agregue al menos una llanta a la factura"
            )
            return

        total_text = self.total_input.text().strip().replace(",", "")
        if not total_text:
            QMessageBox.warning(self, "Validación", "El total es obligatorio")
            self.total_input.setFocus()
            return

        try:
            total = Decimal(total_text)
        except Exception:
            QMessageBox.warning(self, "Validación", "Total inválido")
            return

        if total <= 0:
            QMessageBox.warning(self, "Validación", "El total debe ser mayor a cero")
            return

        self.accept()

    def get_data(self) -> dict:
        total_text = self.total_input.text().strip().replace(",", "")
        total = Decimal(total_text or "0")
        obs = self.observaciones_input.toPlainText().strip() or None
        plazo = self.plazo_spin.value()
        items = [
            {
                "llanta_id": it["llanta_id"],
                "precio_unitario": it["precio"],
            }
            for it in self._items
        ]
        return {
            "cliente_id": self.cliente_combo.currentData(),
            "total": total,
            "observaciones": obs,
            "plazo_dias": plazo,
            "items": items,
        }


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


class AbonosDialog(QDialog):
    """Dialog showing payment history for an invoice."""

    def __init__(self, factura: Factura, pagos: list, parent=None):
        super().__init__(parent)
        self.factura = factura
        self.setWindowTitle(f"Abonos - {factura.numero}")
        self.resize(550, 320)
        self.setup_ui(pagos)

    def setup_ui(self, pagos):
        layout = QVBoxLayout()

        info = QLabel(
            f"Factura: {self.factura.numero}  |  "
            f"Total: ${self.factura.total:,.2f}  |  "
            f"Saldo: ${self.factura.saldo:,.2f}  |  "
            f"Plazo: {self.factura.plazo_dias or 30} d\u00edas"
        )
        info.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px;")
        layout.addWidget(info)

        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Fecha", "M\u00e9todo", "Referencia", "Valor"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)

        table.setRowCount(len(pagos))
        for row, p in enumerate(pagos):
            table.setItem(row, 0, QTableWidgetItem(p.fecha.strftime("%Y-%m-%d %H:%M")))
            table.setItem(row, 1, QTableWidgetItem(p.metodo_pago))
            table.setItem(row, 2, QTableWidgetItem(p.referencia or "\u2014"))
            table.setItem(row, 3, QTableWidgetItem(f"${p.valor:,.2f}"))

        layout.addWidget(table)

        cerrar = QPushButton("Cerrar")
        cerrar.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        cerrar.clicked.connect(self.accept)
        layout.addWidget(cerrar)

        self.setLayout(layout)


class FacturacionView(QWidget):
    """Invoice management view with table, search, filter, create and payment."""

    COLUMNAS = [
        "ID",
        "N\u00famero",
        "Cliente",
        "Fecha",
        "Total",
        "Abonos",
        "Saldo",
        "Estado",
        "Observaciones",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._timer_activo = False
        self.setup_ui()
        try:
            self._cargar_datos()
        except Exception as e:
            print(f"[FacturacionView] Error al cargar datos iniciales: {e}")
            # Show placeholder in table area so UI stays visible
            self.tabla.setRowCount(1)
            self.tabla.setColumnCount(1)
            self.tabla.setHorizontalHeaderLabels(["Error"])
            item = QTableWidgetItem(f"No se pudieron cargar los datos: {e}")
            item.setForeground(QColor("#e74c3c"))
            self.tabla.setItem(0, 0, item)
            self.tabla.horizontalHeader().setStretchLastSection(True)

    def _safe_reload(self) -> None:
        """Reload data with error handling for late-initialization safety."""
        try:
            self._cargar_datos()
        except Exception as e:
            print(f"[FacturacionView] Error al recargar datos: {e}")
            # don't replace table content at all if reload fails

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # ── Header ──
        header = QLabel("Facturaci\u00f3n")
        header.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #3498db; padding: 10px 0;"
        )
        layout.addWidget(header)

        # ── Search row ──
        search_row = QHBoxLayout()

        self.buscar_input = QLineEdit()
        self.buscar_input.setPlaceholderText("Buscar por nombre, NIT, tel\u00e9fono...")
        self.buscar_input.setStyleSheet(
            "font-size: 14px; padding: 6px 12px; border: 1px solid #ccc; "
            "border-radius: 15px; max-width: 350px;"
        )
        self.buscar_input.setMaximumWidth(350)
        self.buscar_input.textChanged.connect(self._on_search)
        search_row.addWidget(self.buscar_input)

        search_row.addWidget(QLabel("Cliente:"))
        self.filtro_cliente = QComboBox()
        self.filtro_cliente.setStyleSheet(
            "font-size: 14px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; min-width: 180px;"
        )
        self._cargar_clientes_filter()
        self.filtro_cliente.currentIndexChanged.connect(self._safe_reload)
        search_row.addWidget(self.filtro_cliente)

        search_row.addWidget(QLabel("Estado:"))
        self.filtro_estado = QComboBox()
        self.filtro_estado.addItems(["Todas", "PENDIENTE", "PAGADA", "ANULADA", "GARANTIA"])
        self.filtro_estado.setStyleSheet(
            "font-size: 14px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px;"
        )
        self.filtro_estado.currentTextChanged.connect(self._safe_reload)
        search_row.addWidget(self.filtro_estado)

        search_row.addStretch()
        layout.addLayout(search_row)

        # ── Action buttons ──
        action_row = QHBoxLayout()

        refresh_btn = QPushButton("Actualizar")
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        refresh_btn.clicked.connect(self._safe_reload)
        action_row.addWidget(refresh_btn)

        nuevo_btn = QPushButton("+ Nueva Factura")
        nuevo_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #219a52; }"
        )
        nuevo_btn.clicked.connect(self._nueva_factura)
        action_row.addWidget(nuevo_btn)

        pagar_btn = QPushButton("Registrar Pago")
        pagar_btn.setStyleSheet(
            "QPushButton { background-color: #f39c12; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #e67e22; }"
        )
        pagar_btn.clicked.connect(self._registrar_pago)
        action_row.addWidget(pagar_btn)

        anular_btn = QPushButton("Anular")
        anular_btn.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #c0392b; }"
        )
        anular_btn.clicked.connect(self._anular_factura)
        action_row.addWidget(anular_btn)

        precios_btn = QPushButton("PRECIOS")
        precios_btn.setStyleSheet(
            "QPushButton { background-color: #8e44ad; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #7d3c98; }"
        )
        precios_btn.clicked.connect(self._abrir_precios)
        action_row.addWidget(precios_btn)

        action_row.addStretch()
        layout.addLayout(action_row)

        # ── Table ──
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
        self.table.setStyleSheet(
            "QTableWidget { font-size: 13px; }"
            "QHeaderView::section { font-weight: bold; font-size: 13px; }"
        )
        self.table.cellClicked.connect(self._on_cell_clicked)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _cargar_clientes_filter(self) -> None:
        clientes = ClienteService.listar_clientes()
        self.filtro_cliente.clear()
        self.filtro_cliente.addItem("Todos los clientes", None)
        for c in clientes:
            if c.activo:
                self.filtro_cliente.addItem(f"{c.nombre} ({c.nit})", c.id)

    def _on_search(self) -> None:
        if self._timer_activo:
            return
        self._timer_activo = True
        QTimer.singleShot(300, self._cargar_datos_con_busqueda)

    def _cargar_datos_con_busqueda(self) -> None:
        self._timer_activo = False
        self._safe_reload()

    def _cargar_datos(self) -> None:
        termino = self.buscar_input.text().strip()
        estado = self.filtro_estado.currentText()
        if estado == "Todas":
            estado = None
        cliente_id = self.filtro_cliente.currentData()

        if termino or cliente_id:
            facturas = FacturaService.buscar(
                termino=termino, estado=estado, cliente_id=cliente_id
            )
        else:
            facturas = FacturaService.listar_facturas(estado=estado, cliente_id=cliente_id)
        self._poblar_tabla(facturas)

    def _poblar_tabla(self, facturas: list[Factura]) -> None:
        self.table.setRowCount(len(facturas))

        for row, f in enumerate(facturas):
            # 0 - ID (hidden)
            self.table.setItem(row, 0, QTableWidgetItem(str(f.id)))
            # 1 - N\u00famero
            self.table.setItem(row, 1, QTableWidgetItem(f.numero))
            # 2 - Cliente
            nombre_cliente = f.cliente.nombre if f.cliente else "?"
            self.table.setItem(row, 2, QTableWidgetItem(nombre_cliente))
            # 3 - Fecha
            self.table.setItem(
                row, 3, QTableWidgetItem(f.fecha_emision.strftime("%Y-%m-%d"))
            )
            # 4 - Total
            self.table.setItem(row, 4, QTableWidgetItem(f"${f.total:,.2f}"))
            # 5 - Abonos (clickeable)
            total_abonos = f.total - f.saldo
            abono_item = QTableWidgetItem(f"${total_abonos:,.2f}")
            abono_item.setData(Qt.ItemDataRole.UserRole, f.id)
            if total_abonos > 0:
                abono_item.setForeground(QColor("#2980b9"))
                abono_item.setToolTip("Click para ver detalle de abonos")
            self.table.setItem(row, 5, abono_item)
            # 6 - Saldo
            saldo_item = QTableWidgetItem(f"${f.saldo:,.2f}")
            if f.saldo > 0:
                saldo_item.setForeground(QColor("#e74c3c"))
            else:
                saldo_item.setForeground(QColor("#27ae60"))
            self.table.setItem(row, 6, saldo_item)
            # 7 - Estado
            self.table.setItem(row, 7, QTableWidgetItem(f.estado))
            # 8 - Observaciones
            obs_text = f.observaciones or ""
            obs_item = QTableWidgetItem(obs_text[:60] + "..." if len(obs_text) > 60 else obs_text)
            if obs_text:
                obs_item.setToolTip(obs_text)
            self.table.setItem(row, 8, obs_item)

        # Hide ID column
        self.table.setColumnHidden(0, True)

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Handle cell clicks - open AbonosDialog on Abonos column."""
        if col == 5:  # Abonos column
            factura_id = int(self.table.item(row, 0).text())
            factura = FacturaService.obtener_por_id(factura_id)
            if factura:
                pagos = FacturaService.obtener_pagos(factura_id)
                dialog = AbonosDialog(factura, pagos, self)
                dialog.exec()

    def _abrir_precios(self) -> None:
        """Open the standalone PreciosDisenoDialog (costo + 3 precios por diseño+dimensión)."""
        dialog = PreciosDisenoDialog(self)
        dialog.exec()

    def _nueva_factura(self) -> None:
        dialog = FacturaFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        ok, resultado = FacturaService.crear(
            cliente_id=data["cliente_id"],
            total=data["total"],
            observaciones=data["observaciones"],
            plazo_dias=data["plazo_dias"],
            items=data["items"],
        )

        if ok:
            self._cargar_datos()
            assert isinstance(resultado, Factura)
            QMessageBox.information(
                self, "\u00c9xito", f"Factura {resultado.numero} creada"
            )
        else:
            QMessageBox.warning(self, "Error", str(resultado))

    def _registrar_pago(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Seleccionar", "Seleccione una factura de la tabla"
            )
            return

        factura_id = int(self.table.item(row, 0).text())
        factura = FacturaService.obtener_por_id(factura_id)
        if not factura:
            QMessageBox.warning(self, "Error", "Factura no encontrada")
            return

        if factura.estado == "ANULADA":
            QMessageBox.warning(
                self, "Error", "No se pueden registrar pagos en facturas anuladas"
            )
            return
        if factura.estado == "PAGADA":
            QMessageBox.information(
                self, "Info", "Esta factura ya est\u00e1 pagada"
            )
            return

        dialog = PagoDialog(factura, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        valor, metodo, ref = dialog.get_data()
        ok, msg = FacturaService.registrar_pago(
            factura_id=factura_id,
            valor=valor,
            metodo_pago=metodo,
            referencia=ref,
        )

        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "\u00c9xito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _anular_factura(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Seleccionar", "Seleccione una factura de la tabla"
            )
            return

        factura_id = int(self.table.item(row, 0).text())
        num = self.table.item(row, 1).text()

        confirm = QMessageBox.question(
            self,
            "Confirmar anulaci\u00f3n",
            f"\u00bfEst\u00e1 seguro de anular la factura {num}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, msg = FacturaService.anular(factura_id)
        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "\u00c9xito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)
