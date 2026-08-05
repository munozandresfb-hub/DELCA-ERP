from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
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

from src.modules.clientes.repositories.cliente_repository import ClienteRepository
from src.database.engine import get_session
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.repositories.llanta_repository import LlantaRepository
from src.modules.llantas.services.llanta_service import (
    ESTADOS_PROCESO,
    UBICACIONES_DISPLAY,
    LlantaService,
)
from src.modules.llantas.services.tiquete_printer import TiquetePrinter
from src.modules.llantas.viewmodels.llanta_viewmodel import LlantaViewModel
from src.modules.llantas.views.catalogos_view import CatalogoMaestroDialog
from src.modules.inventario.services.precio_producto_service import PrecioProductoService


class LlantaFormDialog(QDialog):
    """Dialog for registering a new tire — simplified form for shop-floor use."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Registrar Llanta")
        self.resize(520, 620)
        self._clientes_dict: dict[str, int] = {}
        self._clientes_info: dict[int, dict] = {}
        self._tiquete_duplicado = False
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # ═══════════════ Tiquete ═══════════════
        self.tiquete_input = QLineEdit()
        self.tiquete_input.setPlaceholderText("Número de tiquete")
        self.tiquete_input.textChanged.connect(self._on_tiquete_cambiado)

        # Validación en vivo con debounce: consulta la BD solo tras 400 ms
        # sin escritura, para no golpear la BD en cada tecla.
        self._tiquete_timer = QTimer(self)
        self._tiquete_timer.setSingleShot(True)
        self._tiquete_timer.setInterval(400)
        self._tiquete_timer.timeout.connect(self._verificar_tiquete_en_vivo)

        # Label de error inline bajo el campo (oculto por defecto)
        self.tiquete_error_label = QLabel("")
        self.tiquete_error_label.setStyleSheet(
            "color: #c62828; font-size: 12px; font-weight: 600;"
        )
        self.tiquete_error_label.setWordWrap(True)
        self.tiquete_error_label.hide()

        # ═══════════════ Orden de Servicio ═══════════════
        orden_group = QFormLayout()
        orden_group.setHorizontalSpacing(12)

        self.numero_orden_input = QLineEdit()
        self.numero_orden_input.setPlaceholderText("Ej: OS-2024-001")
        self.consecutivo_input = QLineEdit()
        self.consecutivo_input.setPlaceholderText("Consecutivo interno")
        self.fecha_ingreso_edit = QDateEdit()
        self.fecha_ingreso_edit.setCalendarPopup(True)
        self.fecha_ingreso_edit.setDate(QDate.currentDate())

        orden_group.addRow("N° Orden:", self.numero_orden_input)
        orden_group.addRow("Consecutivo:", self.consecutivo_input)
        orden_group.addRow("Fecha Ingreso:", self.fecha_ingreso_edit)

        # ═══════════════ Cliente ═══════════════
        cliente_group = QFormLayout()
        cliente_group.setHorizontalSpacing(12)

        self.cliente_input = QLineEdit()
        self.cliente_input.setPlaceholderText("Escriba nombre del cliente...")
        self.cliente_input.textEdited.connect(self._on_cliente_edited)

        # Load clientes
        with get_session() as session:
            clientes = ClienteRepository.get_activos(session)
            for c in clientes:
                label = f"{c.nombre} ({c.nit})"
                self._clientes_dict[label] = c.id
                self._clientes_info[c.id] = {
                    "nit": c.nit or "",
                    "telefono": c.telefono or "",
                    "direccion": c.direccion or "",
                }

        completer = QCompleter(list(self._clientes_dict.keys()), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.activated.connect(self._on_cliente_selected)
        self.cliente_input.setCompleter(completer)

        # Read-only client info labels
        self.nit_label = QLabel("—")
        self.nit_label.setStyleSheet("color: #555;")
        self.telefono_label = QLabel("—")
        self.telefono_label.setStyleSheet("color: #555;")
        self.direccion_label = QLabel("—")
        self.direccion_label.setStyleSheet("color: #555;")
        self.direccion_label.setWordWrap(True)

        cliente_group.addRow("Cliente:", self.cliente_input)
        cliente_group.addRow("NIT:", self.nit_label)
        cliente_group.addRow("Teléfono:", self.telefono_label)
        cliente_group.addRow("Dirección:", self.direccion_label)

        # ═══════════════ Datos Llanta ═══════════════
        llanta_group = QFormLayout()
        llanta_group.setHorizontalSpacing(12)

        self.marca_combo = QComboBox()
        self.marca_combo.addItem("-- Seleccionar Marca --", None)
        for m in LlantaService.listar_marcas():
            self.marca_combo.addItem(m.nombre, m.id)

        self.dimension_combo = QComboBox()
        self.dimension_combo.addItem("-- Seleccionar Dimensión --", None)
        for d in LlantaService.listar_dimensiones():
            self.dimension_combo.addItem(d.display, d.id)
        self.dimension_combo.currentIndexChanged.connect(self._auto_cargar_precio)

        self.diseno_combo = QComboBox()
        self.diseno_combo.addItem("-- Seleccionar Diseño --", None)
        for d in LlantaService.listar_disenos():
            self.diseno_combo.addItem(d.nombre, d.id)
        self.diseno_combo.currentIndexChanged.connect(self._auto_cargar_precio)

        self.dot_input = QLineEdit()
        self.dot_input.setPlaceholderText("Ej: DOT XXXX XXXX XXXX")

        self.asesor_input = QLineEdit()
        self.asesor_input.setPlaceholderText("Nombre del asesor comercial")

        self.precio_venta_spin = QDoubleSpinBox()
        self.precio_venta_spin.setRange(0, 9999999)
        self.precio_venta_spin.setPrefix("$ ")
        self.precio_venta_spin.setSpecialValueText("—")
        self.precio_venta_spin.setDecimals(2)

        llanta_group.addRow("Marca:", self.marca_combo)
        llanta_group.addRow("Dimensión:", self.dimension_combo)
        llanta_group.addRow("Diseño:", self.diseno_combo)
        llanta_group.addRow("DOT:", self.dot_input)
        llanta_group.addRow("Asesor:", self.asesor_input)
        llanta_group.addRow("Precio Venta:", self.precio_venta_spin)

        # ═══════════════ Observaciones ═══════════════
        self.observaciones_input = QTextEdit()
        self.observaciones_input.setPlaceholderText("Observaciones de la orden...")
        self.observaciones_input.setMaximumHeight(70)

        # ── Assemble ────────────────────────────────────────────────
        sections = QVBoxLayout()
        sections.setSpacing(10)

        # Tiquete
        tiquete_row = QHBoxLayout()
        tiquete_row.addWidget(QLabel("Tiquete *:"))
        tiquete_row.addWidget(self.tiquete_input, 1)
        tiquete_box = QVBoxLayout()
        tiquete_box.addLayout(tiquete_row)
        tiquete_box.addWidget(self.tiquete_error_label)
        sections.addLayout(tiquete_box)

        # Orden de Servicio section
        orden_title = QLabel("── Orden de Servicio ──")
        orden_title.setStyleSheet("font-weight: bold; color: #2c3e50; margin-top: 4px;")
        sections.addWidget(orden_title)
        sections.addLayout(orden_group)

        # Cliente section
        cliente_title = QLabel("── Datos del Cliente ──")
        cliente_title.setStyleSheet("font-weight: bold; color: #2c3e50; margin-top: 4px;")
        sections.addWidget(cliente_title)
        sections.addLayout(cliente_group)

        # Llanta section
        llanta_title = QLabel("── Datos de la Llanta ──")
        llanta_title.setStyleSheet("font-weight: bold; color: #2c3e50; margin-top: 4px;")
        sections.addWidget(llanta_title)
        sections.addLayout(llanta_group)

        sections.addWidget(QLabel("Observaciones:"))
        sections.addWidget(self.observaciones_input)

        layout.addLayout(sections)

        # Buttons
        btn_layout = QHBoxLayout()
        self.guardar_btn = QPushButton("Guardar")
        self.guardar_btn.setStyleSheet(
            "QPushButton { background: #2e7d32; color: white; font-weight: bold; "
            "padding: 8px 24px; border-radius: 4px; border: none; }"
        )
        self.guardar_btn.clicked.connect(self._guardar)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.setStyleSheet(
            "QPushButton { padding: 8px 24px; border-radius: 4px; }"
        )
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.guardar_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    # ── Client events ──────────────────────────────────────────────

    def _on_cliente_edited(self, text: str) -> None:
        """Reset client info labels only when text doesn't match any known client."""
        if not text:
            self.nit_label.setText("—")
            self.telefono_label.setText("—")
            self.direccion_label.setText("—")
            return
        # Keep current labels if text still matches the currently selected client
        for label, cid in self._clientes_dict.items():
            if text.lower() in label.lower():
                return  # still matches a client — don't reset
        self.nit_label.setText("—")
        self.telefono_label.setText("—")
        self.direccion_label.setText("—")

    def _on_cliente_selected(self, text: str) -> None:
        """Called when completer activates — show NIT, tel, dirección."""
        cliente_id = self._clientes_dict.get(text)
        if not cliente_id:
            return
        info = self._clientes_info.get(cliente_id, {})
        self.nit_label.setText(info.get("nit", "—"))
        self.telefono_label.setText(info.get("telefono", "—"))
        self.direccion_label.setText(info.get("direccion", "—"))

    # ── Diseños: independientes de la marca (combo cargado al inicio) ──

    def _auto_cargar_precio(self) -> None:
        """Auto-fill precio_venta from PrecioProducto when both combos are selected."""
        diseno_id = self.diseno_combo.currentData()
        dimension_id = self.dimension_combo.currentData()
        if not diseno_id or not dimension_id:
            return
        resultados = PrecioProductoService.listar(diseno_id=diseno_id, dimension_id=dimension_id)
        if not resultados:
            return
        p = resultados[0]
        self.precio_venta_spin.setValue(float(p.precio_normal))

    # ── Validación en vivo del tiquete ──────────────────────────────

    def _on_tiquete_cambiado(self) -> None:
        """Reinicia el debounce: solo se consulta la BD tras 400 ms sin escribir."""
        self._tiquete_timer.start()

    def _verificar_tiquete_en_vivo(self) -> None:
        """Consulta la BD: si el tiquete ya está asignado, muestra error
        inmediato (sin esperar a Guardar) y bloquea el guardado."""
        tiquete = self.tiquete_input.text().strip()
        if not tiquete:
            self._tiquete_duplicado = False
            self.tiquete_error_label.hide()
            self.guardar_btn.setEnabled(True)
            return

        duplicado = LlantaService.tiquete_existe(tiquete)
        self._tiquete_duplicado = duplicado
        if duplicado:
            self.tiquete_error_label.setText(
                f"El tiquete '{tiquete}' ya está asignado a otra llanta"
            )
            self.tiquete_error_label.show()
            self.tiquete_input.setStyleSheet(
                "QLineEdit { border: 1px solid #c62828; }"
            )
            self.guardar_btn.setEnabled(False)
        else:
            self.tiquete_error_label.hide()
            self.tiquete_input.setStyleSheet("")
            self.guardar_btn.setEnabled(True)

    # ── Validation & save ──────────────────────────────────────────

    def _guardar(self) -> None:
        tiquete = self.tiquete_input.text().strip()
        if not tiquete:
            QMessageBox.warning(self, "Validación", "El Tiquete es obligatorio")
            self.tiquete_input.setFocus()
            return
        if self._tiquete_duplicado:
            QMessageBox.warning(
                self,
                "Validación",
                f"El tiquete '{tiquete}' ya está asignado a otra llanta",
            )
            self.tiquete_input.setFocus()
            return
        if not self.marca_combo.currentData():
            QMessageBox.warning(self, "Validación", "Debe seleccionar una marca")
            self.marca_combo.setFocus()
            return
        if not self.dimension_combo.currentData():
            QMessageBox.warning(self, "Validación", "Debe seleccionar una dimensión")
            self.dimension_combo.setFocus()
            return
        if not self.cliente_input.text().strip():
            QMessageBox.warning(self, "Validación", "Debe seleccionar un cliente")
            self.cliente_input.setFocus()
            return
        self.accept()

    def get_data(self) -> dict:
        cliente_texto = self.cliente_input.text().strip()
        cliente_id = self._clientes_dict.get(cliente_texto)
        return {
            "tiquete": self.tiquete_input.text().strip(),
            "numero_orden": self.numero_orden_input.text().strip() or None,
            "consecutivo": self.consecutivo_input.text().strip() or None,
            "fecha_ingreso": self.fecha_ingreso_edit.date().toPython(),
            "marca_id": self.marca_combo.currentData(),
            "dimension_id": self.dimension_combo.currentData(),
            "diseno_id": self.diseno_combo.currentData(),
            "dot": self.dot_input.text().strip() or None,
            "asesor": self.asesor_input.text().strip() or None,
            "precio_venta": self.precio_venta_spin.value() or None,
            "observaciones": self.observaciones_input.toPlainText().strip() or None,
            "cliente_id": cliente_id,
        }


class HistorialDialog(QDialog):
    """Dialog to show state/location history of a tire."""

    def __init__(
        self,
        llanta: Llanta,
        estados: list,
        ubicaciones: list,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Historial - {llanta.tiquete}")
        self.resize(500, 400)
        self.setup_ui(estados, ubicaciones)

    def setup_ui(self, estados: list, ubicaciones: list) -> None:
        layout = QVBoxLayout()

        # Estados
        layout.addWidget(QLabel("Historial de Estados:"))
        estados_table = QTableWidget()
        estados_table.setColumnCount(2)
        estados_table.setHorizontalHeaderLabels(["Estado", "Fecha"])
        estados_table.setRowCount(len(estados))
        estados_table.horizontalHeader().setStretchLastSection(True)
        for i, e in enumerate(estados):
            estados_table.setItem(i, 0, QTableWidgetItem(e.estado))
            estados_table.setItem(
                i, 1, QTableWidgetItem(str(e.fecha)[:19])
            )
        layout.addWidget(estados_table)

        # Ubicaciones
        layout.addWidget(QLabel("Historial de Ubicaciones:"))
        ubicaciones_table = QTableWidget()
        ubicaciones_table.setColumnCount(2)
        ubicaciones_table.setHorizontalHeaderLabels(["Ubicación", "Fecha"])
        ubicaciones_table.setRowCount(len(ubicaciones))
        ubicaciones_table.horizontalHeader().setStretchLastSection(True)
        for i, u in enumerate(ubicaciones):
            ubicaciones_table.setItem(i, 0, QTableWidgetItem(u.ubicacion))
            ubicaciones_table.setItem(
                i, 1, QTableWidgetItem(str(u.fecha)[:19])
            )
        layout.addWidget(ubicaciones_table)

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)


class CambioRapidoDialog(QDialog):
    """Dialog for quick state change by entering tire code directly."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cambio Rápido de Estado")
        self.resize(380, 180)
        self._llanta_encontrada: Llanta | None = None
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        form = QFormLayout()
        self.tiquete_input = QLineEdit()
        self.tiquete_input.setPlaceholderText("Tiquete de la llanta...")
        self.tiquete_input.textChanged.connect(self._buscar_llanta)
        form.addRow("Tiquete:", self.tiquete_input)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #666;")
        form.addRow(self.info_label)

        self.estado_combo = QComboBox()
        for est in ESTADOS_PROCESO:
            self.estado_combo.addItem(est)
        self.estado_combo.setEnabled(False)
        form.addRow("Nuevo Estado:", self.estado_combo)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.guardar_btn = QPushButton("Cambiar")
        self.guardar_btn.clicked.connect(self.accept)
        self.guardar_btn.setEnabled(False)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.guardar_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _buscar_llanta(self) -> None:
        tiquete = self.tiquete_input.text().strip()
        if not tiquete:
            self.info_label.setText("")
            self.estado_combo.setEnabled(False)
            self.guardar_btn.setEnabled(False)
            self._llanta_encontrada = None
            return

        with get_session() as s:
            llanta = LlantaRepository.get_by_tiquete(s, tiquete)
        self._llanta_encontrada = llanta
        if llanta:
            self.info_label.setText(
                f"✓ {llanta.marca} {llanta.dimension} — Estado: {llanta.estado}"
            )
            self.info_label.setStyleSheet("color: #2e7d32;")
            idx = self.estado_combo.findText(llanta.estado or "")
            if idx >= 0:
                self.estado_combo.setCurrentIndex(idx)
            self.estado_combo.setEnabled(True)
            self.guardar_btn.setEnabled(True)
        else:
            self.info_label.setText("✗ Llanta no encontrada")
            self.info_label.setStyleSheet("color: #c62828;")
            self.estado_combo.setEnabled(False)
            self.guardar_btn.setEnabled(False)

    @property
    def llanta_encontrada(self) -> Llanta | None:
        return self._llanta_encontrada

    @property
    def nuevo_estado(self) -> str:
        return self.estado_combo.currentText()


class LlantasView(QWidget):
    """Full tire management view with table, filters and state control."""

    COLUMNAS = [
        "ID",  # hidden, used for row lookups
        "Cliente",
        "Tiquete",
        "N° Orden",
        "Dimensión",
        "Diseño",
        "Estado",
        "Ubicación Actual",
        "Fecha de Ingreso",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.viewmodel = LlantaViewModel()
        self.setup_ui()
        self._cargar_datos()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # Header
        header = QLabel("Módulo Llantas")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px 0;"
        )
        layout.addWidget(header)

        # Search + Filter row
        row1 = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por tiquete, marca o dimensión...")
        self.search_input.textChanged.connect(self._buscar)
        row1.addWidget(self.search_input)

        self.estado_filter = QComboBox()
        self.estado_filter.addItem("Todos los estados", "")
        for est in ESTADOS_PROCESO:
            self.estado_filter.addItem(est, est)
        self.estado_filter.currentIndexChanged.connect(
            self._filtrar_estado
        )
        row1.addWidget(QLabel("Estado:"))
        row1.addWidget(self.estado_filter)

        layout.addLayout(row1)

        # Buttons row
        row2 = QHBoxLayout()

        nueva_btn = QPushButton("+ Nueva Llanta")
        nueva_btn.clicked.connect(self._nueva_llanta)
        row2.addWidget(nueva_btn)

        cambio_rapido_btn = QPushButton("⚡ Cambio Rápido")
        cambio_rapido_btn.clicked.connect(self._cambio_rapido)
        row2.addWidget(cambio_rapido_btn)

        historial_btn = QPushButton("Ver Historial")
        historial_btn.clicked.connect(self._ver_historial)
        row2.addWidget(historial_btn)

        imprimir_btn = QPushButton("🖨 Imprimir Tiquete")
        imprimir_btn.clicked.connect(self._imprimir_tiquete)
        row2.addWidget(imprimir_btn)

        catalogos_btn = QPushButton("📋 Catálogos")
        catalogos_btn.setStyleSheet(
            "QPushButton { background: #6c757d; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; border: none; }"
        )
        catalogos_btn.clicked.connect(self._abrir_catalogos)
        row2.addWidget(catalogos_btn)

        layout.addLayout(row2)

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
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _cargar_datos(self) -> None:
        self.viewmodel.cargar_llantas()
        self._poblar_tabla()

    def _poblar_tabla(self) -> None:
        llantas = self.viewmodel.llantas
        self.table.setRowCount(len(llantas))

        for row, l in enumerate(llantas):
            self.table.setItem(row, 0, QTableWidgetItem(str(l.id)))
            nombre_cliente = l.cliente.nombre if l.cliente else "Sin cliente"
            self.table.setItem(row, 1, QTableWidgetItem(nombre_cliente))
            self.table.setItem(row, 2, QTableWidgetItem(l.tiquete or ""))
            self.table.setItem(row, 3, QTableWidgetItem(l.numero_orden or "—"))
            dim = l.dimension_obj.display if l.dimension_obj else (l.dimension or "—")
            self.table.setItem(row, 4, QTableWidgetItem(dim))
            dis = l.diseno_obj.nombre if l.diseno_obj else "—"
            self.table.setItem(row, 5, QTableWidgetItem(dis))
            self.table.setItem(row, 6, QTableWidgetItem(l.estado or ""))
            ubic_raw = l.ubicacion_actual or "—"
            ubic_str = (
                UBICACIONES_DISPLAY.get(ubic_raw, ubic_raw)
                if ubic_raw != "—"
                else "—"
            )
            self.table.setItem(row, 7, QTableWidgetItem(ubic_str))
            fecha = l.fecha_ingreso.strftime("%Y-%m-%d") if l.fecha_ingreso else "—"
            self.table.setItem(row, 8, QTableWidgetItem(fecha))

        self.table.setColumnHidden(0, True)

    def _buscar(self) -> None:
        termino = self.search_input.text()
        self.viewmodel.buscar(termino)
        self._poblar_tabla()

    def _filtrar_estado(self) -> None:
        estado = self.estado_filter.currentData()
        self.viewmodel.filtrar_por_estado(estado or None)
        self._poblar_tabla()

    def _nueva_llanta(self) -> None:
        dialog = LlantaFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        ok, msg = self.viewmodel.crear(**data)

        if ok:
            self._poblar_tabla()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _cambio_rapido(self) -> None:
        dialog = CambioRapidoDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        llanta = dialog.llanta_encontrada
        if not llanta:
            return

        ok, msg = self.viewmodel.cambiar_estado(
            llanta.id, dialog.nuevo_estado
        )
        if ok:
            self._poblar_tabla()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _ver_historial(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Seleccionar",
                "Seleccione una llanta de la tabla",
            )
            return

        llanta_id = int(self.table.item(row, 0).text())
        llanta = self.viewmodel.obtener_por_id(llanta_id)
        if not llanta:
            QMessageBox.warning(self, "Error", "Llanta no encontrada")
            return

        estados = LlantaService.obtener_historial_estados(llanta_id)
        ubicaciones = LlantaService.obtener_historial_ubicaciones(
            llanta_id
        )

        dialog = HistorialDialog(llanta, estados, ubicaciones, self)
        dialog.exec()

    def _abrir_catalogos(self) -> None:
        """Open the master catalogs dialog. Combos refresh on next LlantaFormDialog open."""
        dialog = CatalogoMaestroDialog(self)
        dialog.exec()

    def _imprimir_tiquete(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Seleccionar",
                "Seleccione una llanta de la tabla",
            )
            return

        llanta_id = int(self.table.item(row, 0).text())
        llanta = self.viewmodel.obtener_por_id(llanta_id)
        if not llanta:
            QMessageBox.warning(self, "Error", "Llanta no encontrada")
            return

        ok, msg = TiquetePrinter.print_tiquete(llanta, self)
        if ok:
            QMessageBox.information(self, "Impresión", msg)
        else:
            QMessageBox.warning(self, "Impresión", msg)
