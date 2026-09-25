from decimal import Decimal
import logging

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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

from src.database.engine import get_session
from src.modules.clientes.services.cliente_service import ClienteService
from src.modules.finanzas.services.factura_service import FacturaService
from src.modules.finanzas.views.facturacion_view._llantas_picker_dialog import (
    LlantasPickerDialog,
)
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.services.costo_precio import costo_precio, indice_precios
from src.modules.llantas.services.llanta_service._core import formatear_tiquete

logger = logging.getLogger("delca.views")


class FacturaFormDialog(QDialog):
    """Dialog for creating a new invoice from billed tires.

    One or more tires can be added; each line pre-fills its price from the
    price catalog (``precios_producto`` por diseño + dimensión: precio_normal
    → precio_minimo → 1 peso sin cobertura) and can be edited. The total
    pre-fills as the sum of line prices but stays manually editable —
    the final total is the amount charged to the client.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nueva Factura")
        self.resize(680, 580)
        self._clientes: list[tuple[int, str]] = []
        self._items: list[dict] = []
        self._llantas_dict: dict[int, Llanta] = {}
        # Índice de precios del catálogo (rápido) — las llantas del cliente se
        # cargan bajo demanda en el diálogo de selección (formulario ágil).
        try:
            with get_session() as s:
                self._idx_precios: dict[tuple[int, int], dict] = indice_precios(s)
        except Exception as e:
            logger.error("Error cargando índice de precios: %s", e, exc_info=True)
            self._idx_precios = {}
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
        # Precarga: al hacer click abre la ventana emergente con las llantas
        # del cliente seleccionado (pendientes de facturación).
        self.seleccionar_btn = QPushButton("➕ Seleccionar llantas del cliente")
        self.seleccionar_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; border: none; }"
            "QPushButton:hover { background-color: #219a52; }"
        )
        self.seleccionar_btn.clicked.connect(self._seleccionar_llantas)
        self.seleccionar_btn.setEnabled(False)
        picker_row.addWidget(self.seleccionar_btn)

        llanta_nueva_btn = QPushButton("Llanta nueva")
        llanta_nueva_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; border: none; }"
            "QPushButton:hover { background-color: #219a52; }"
        )
        llanta_nueva_btn.clicked.connect(self._agregar_llanta_nueva)
        picker_row.addWidget(llanta_nueva_btn)
        form.addRow(picker_row)

        # Items table: Tipo | Tiquete | Dimensión | Diseño | Precio | Acción
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(
            ["Tipo", "Tiquete", "Dimensión", "Diseño", "Precio", ""]
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.items_table.setColumnWidth(4, 130)
        self.items_table.setColumnWidth(5, 60)
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
        self.cliente_combo.addItem("-- Seleccionar cliente --", None)
        for c in clientes:
            if c.activo:
                label = f"{c.nombre} ({c.nit})"
                self.cliente_combo.addItem(label, c.id)
                self._clientes.append((c.id, label))
        self.cliente_combo.currentIndexChanged.connect(
            self._actualizar_boton_llantas
        )

    def _actualizar_boton_llantas(self) -> None:
        """Habilita la precarga de llantas solo con cliente seleccionado."""
        self.seleccionar_btn.setEnabled(
            self.cliente_combo.currentData() is not None
        )

    def _seleccionar_llantas(self) -> None:
        """Abre la ventana emergente con las llantas del cliente
        (pendientes de facturación) y agrega las seleccionadas."""
        cliente_id = self.cliente_combo.currentData()
        if not cliente_id:
            QMessageBox.warning(
                self, "Validación", "Seleccione primero el cliente"
            )
            return
        dialog = LlantasPickerDialog(cliente_id, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        for llanta in dialog.llantas_seleccionadas:
            self._agregar_llanta_obj(llanta)

    def _agregar_llanta_obj(self, llanta: Llanta) -> None:
        """Agrega una llanta (del picker) como línea de la factura."""
        if any(it["llanta_id"] == llanta.id for it in self._items):
            return  # ya está en la factura

        # Precio desde el catálogo (diseño+dimensión): normal → mínimo → 1 sin cobertura
        precio = costo_precio(llanta, self._idx_precios)[1]
        self._items.append(
            {
                "tipo": "Reencauchada",
                "llanta_id": llanta.id,
                "descripcion": None,
                "tiquete": formatear_tiquete(llanta.tiquete),
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

    def _agregar_llanta_nueva(self) -> None:
        """Add a NEW tire (no re-tread record) as a free-text manual line item."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Llanta nueva")
        dialog.setModal(True)
        layout = QVBoxLayout()

        form = QFormLayout()
        input_style = "font-size: 14px; padding: 6px;"
        label_style = "font-size: 14px; font-weight: 600;"

        desc_label = QLabel("Descripción *:")
        desc_label.setStyleSheet(label_style)
        desc_input = QLineEdit()
        desc_input.setPlaceholderText("Ej: Goodyear 295/80 R22.5 nueva")
        desc_input.setStyleSheet(input_style)
        form.addRow(desc_label, desc_input)

        precio_label = QLabel("Precio *:")
        precio_label.setStyleSheet(label_style)
        precio_spin = QDoubleSpinBox()
        precio_spin.setRange(0, 9999999)
        precio_spin.setPrefix("$ ")
        precio_spin.setDecimals(2)
        precio_spin.setStyleSheet(input_style)
        form.addRow(precio_label, precio_spin)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        aceptar_btn = QPushButton("Agregar")
        aceptar_btn.clicked.connect(dialog.accept)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(aceptar_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        desc_input.setFocus()

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        descripcion = desc_input.text().strip()
        if not descripcion:
            QMessageBox.warning(self, "Validación", "La descripción es obligatoria")
            return

        self._items.append(
            {
                "tipo": "Llanta nueva",
                "llanta_id": None,
                "descripcion": descripcion,
                "tiquete": "—",
                "dimension": "—",
                "diseno": "—",
                "precio": precio_spin.value(),
            }
        )
        self._refrescar_tabla_items()

    def _refrescar_tabla_items(self) -> None:
        self.items_table.setRowCount(len(self._items))
        for row, it in enumerate(self._items):
            self.items_table.setItem(row, 0, QTableWidgetItem(it["tipo"]))
            self.items_table.setItem(row, 1, QTableWidgetItem(it["tiquete"]))
            self.items_table.setItem(row, 2, QTableWidgetItem(it["dimension"]))
            self.items_table.setItem(row, 3, QTableWidgetItem(it["diseno"]))
            precio_spin = QDoubleSpinBox()
            precio_spin.setRange(0, 9999999)
            precio_spin.setPrefix("$ ")
            precio_spin.setDecimals(2)
            precio_spin.setValue(it["precio"])
            precio_spin.valueChanged.connect(
                lambda value, r=row: self._on_precio_cambiado(r, value)
            )
            self.items_table.setCellWidget(row, 4, precio_spin)
            quitar_btn = QPushButton("✕")
            quitar_btn.setToolTip("Quitar llanta")
            quitar_btn.setStyleSheet(
                "QPushButton { color: #e74c3c; font-weight: bold; border: none; }"
            )
            quitar_btn.clicked.connect(
                lambda _=False, r=row: self._quitar_llanta(r)
            )
            self.items_table.setCellWidget(row, 5, quitar_btn)
        self._recalcular_total()

    def _on_precio_cambiado(self, row: int, value: float) -> None:
        if 0 <= row < len(self._items):
            self._items[row]["precio"] = value
            self._recalcular_total()

    def _quitar_llanta(self, row: int) -> None:
        if 0 <= row < len(self._items):
            self._items.pop(row)
            self._refrescar_tabla_items()

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
                "descripcion": it.get("descripcion"),
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