from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
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
import logging

from src.database.engine import get_session
from src.modules.clientes.repositories.cliente_repository import ClienteRepository
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.repositories.llanta_repository import LlantaRepository
from src.modules.llantas.services.llanta_service import ESTADOS_PROCESO, LlantaService

logger = logging.getLogger("delca.views")


class LlantaFormDialog(QDialog):
    """Dialog for registering a new tire or editing an existing one.

    Modo edición (llanta != None): carga los datos de la llanta y BLOQUEA el
    tiquete y el precio de venta (inalterables). Se pueden editar: cliente,
    diseño de banda, número de orden, marca, dimensión, DOT, asesor, etc.
    """

    def __init__(self, parent: QWidget | None = None, llanta: Llanta | None = None) -> None:
        super().__init__(parent)
        self._llanta = llanta
        self._imprimir = False
        self.setWindowTitle("Editar Llanta" if llanta else "Registrar Llanta")
        self.resize(520, 620)
        self._clientes_dict: dict[str, int] = {}
        self._clientes_info: dict[int, dict] = {}
        self._tiquete_duplicado = False
        self.setup_ui()
        if llanta:
            self._cargar_llanta(llanta)

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

        # Imprimir (solo al registrar): guarda la llanta y envía la hoja de
        # proceso a la impresora inmediatamente (criterios de impresión intactos).
        self.imprimir_btn = QPushButton("🖨 Imprimir")
        self.imprimir_btn.setStyleSheet(
            "QPushButton { background: #2c3e50; color: white; font-weight: bold; "
            "padding: 8px 24px; border-radius: 4px; border: none; }"
        )
        self.imprimir_btn.clicked.connect(self._guardar_y_imprimir)
        if self._llanta:
            self.imprimir_btn.setVisible(False)  # solo al registrar llantas nuevas

        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.setStyleSheet(
            "QPushButton { padding: 8px 24px; border-radius: 4px; }"
        )
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.guardar_btn)
        btn_layout.addWidget(self.imprimir_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _guardar_y_imprimir(self) -> None:
        """Guarda la llanta y marca que se debe imprimir al terminar."""
        self._imprimir = True
        self._guardar()

    @property
    def imprimir(self) -> bool:
        """True si el usuario pidió imprimir el tiquete tras guardar."""
        return self._imprimir

    def _cargar_llanta(self, llanta: Llanta) -> None:
        """Carga los datos de una llanta existente (modo edición).

        El tiquete y el precio de venta quedan BLOQUEADOS (inalterables).
        """
        self.tiquete_input.setText(llanta.tiquete or "")
        self.tiquete_input.setReadOnly(True)

        self.numero_orden_input.setText(llanta.numero_orden or "")
        self.consecutivo_input.setText(llanta.consecutivo or "")
        if llanta.fecha_ingreso:
            self.fecha_ingreso_edit.setDate(
                QDate(
                    llanta.fecha_ingreso.year,
                    llanta.fecha_ingreso.month,
                    llanta.fecha_ingreso.day,
                )
            )

        if llanta.cliente:
            label = f"{llanta.cliente.nombre} ({llanta.cliente.nit})"
            self.cliente_input.setText(label)
            self._on_cliente_selected(label)

        if llanta.marca_id:
            idx = self.marca_combo.findData(llanta.marca_id)
            if idx >= 0:
                self.marca_combo.setCurrentIndex(idx)
        if llanta.dimension_id:
            idx = self.dimension_combo.findData(llanta.dimension_id)
            if idx >= 0:
                self.dimension_combo.setCurrentIndex(idx)
        if llanta.diseno_id:
            idx = self.diseno_combo.findData(llanta.diseno_id)
            if idx >= 0:
                self.diseno_combo.setCurrentIndex(idx)

        self.dot_input.setText(llanta.dot or "")
        self.asesor_input.setText(llanta.asesor or "")
        self.observaciones_input.setPlainText(llanta.observaciones or "")

        # Precio: bloqueado (muestra el valor actual, no editable)
        self.precio_venta_spin.setEnabled(False)
        self.precio_venta_spin.setValue(float(llanta.precio_venta or 0))

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
        """Auto-fill precio_venta from the price catalog (diseño+dimensión).

        Regla consistente con el resto de la herramienta: precio_normal →
        precio_minimo → 1 peso si la referencia no tiene cobertura.
        """
        diseno_id = self.diseno_combo.currentData()
        dimension_id = self.dimension_combo.currentData()
        if not diseno_id or not dimension_id:
            return
        from types import SimpleNamespace

        from src.modules.llantas.services.costo_precio import (
            costo_precio,
            indice_precios,
        )
        try:
            with get_session() as session:
                idx = indice_precios(session)
        except Exception as e:
            logger.error("Error cargando índice de precios: %s", e, exc_info=True)
            QMessageBox.warning(
                self, "Error", "No se pudo calcular el precio. Consulte el log."
            )
            return
        llanta_proxy = SimpleNamespace(
            dimension_id=dimension_id, diseno_id=diseno_id,
            costo_produccion=0, precio_venta=0,
        )
        _, precio = costo_precio(llanta_proxy, idx)
        self.precio_venta_spin.setValue(precio)

    # ── Validación en vivo del tiquete ──────────────────────────────

    def _on_tiquete_cambiado(self) -> None:
        """Reinicia el debounce: solo se consulta la BD tras 400 ms sin escribir."""
        if self._llanta:
            return  # modo edición: el tiquete es fijo, no validar duplicado
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
        data = {
            "numero_orden": self.numero_orden_input.text().strip() or None,
            "consecutivo": self.consecutivo_input.text().strip() or None,
            "fecha_ingreso": self.fecha_ingreso_edit.date().toPython(),
            "marca_id": self.marca_combo.currentData(),
            "dimension_id": self.dimension_combo.currentData(),
            "diseno_id": self.diseno_combo.currentData(),
            "dot": self.dot_input.text().strip() or None,
            "asesor": self.asesor_input.text().strip() or None,
            "observaciones": self.observaciones_input.toPlainText().strip() or None,
            "cliente_id": cliente_id,
        }
        if not self._llanta:
            # Solo al registrar: tiquete y precio
            data["tiquete"] = self.tiquete_input.text().strip()
            data["precio_venta"] = self.precio_venta_spin.value() or None
        return data


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
        self.setWindowTitle("INSPECCION INICIAL")
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
        self.estado_combo.currentIndexChanged.connect(self._actualizar_estado_causa)
        form.addRow("Nuevo Estado:", self.estado_combo)

        # Causa de rechazo — obligatoria cuando el nuevo estado es RECHAZADA.
        # Se selecciona por número o por texto (autocompletado sobre ambos).
        self.causa_combo = QComboBox()
        self.causa_combo.setEditable(True)
        self.causa_combo.setEnabled(False)
        self.causa_combo.setStyleSheet(
            "QComboBox { font-size: 13px; padding: 4px; border: 1px solid #ccc; "
            "border-radius: 4px; }"
        )
        self.causa_combo.lineEdit().setPlaceholderText("Número o texto de la causa...")
        self._cargar_causas()
        form.addRow("Causa de Rechazo:", self.causa_combo)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.guardar_btn = QPushButton("Cambiar")
        self.guardar_btn.clicked.connect(self._cambiar_y_cerrar)
        self.guardar_btn.setEnabled(False)

        # Cambio Rápido: aplica la inspección y limpia para la siguiente llanta
        # sin cerrar el recuadro (proceso continuo para el usuario).
        self.rapido_btn = QPushButton("⚡ Cambio Rápido")
        self.rapido_btn.setStyleSheet(
            "QPushButton { background: #2c3e50; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; border: none; }"
        )
        self.rapido_btn.clicked.connect(self._cambio_rapido_aplicar)
        self.rapido_btn.setEnabled(False)

        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.guardar_btn)
        btn_layout.addWidget(self.rapido_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _cargar_causas(self) -> None:
        """Carga las causas de rechazo del catálogo (código — descripción)."""
        self.causa_combo.clear()
        causas = LlantaService.listar_causas_rechazo()
        for c in causas:
            self.causa_combo.addItem(f"{c.codigo} — {c.descripcion}", c.id)
        completer = QCompleter(
            [self.causa_combo.itemText(i) for i in range(self.causa_combo.count())],
            self,
        )
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.causa_combo.setCompleter(completer)

    def _actualizar_estado_causa(self) -> None:
        """Habilita la causa de rechazo solo cuando el estado es RECHAZADA."""
        es_rechazada = self.estado_combo.currentText() == "RECHAZADA"
        self.causa_combo.setEnabled(
            es_rechazada and self._llanta_encontrada is not None
        )

    def _resolver_causa_id(self) -> int | None:
        """Resuelve la causa de rechazo escrita (por número o texto).

        Primero busca coincidencia exacta con un item del catálogo (cubre el
        autocompletado del completer, p.ej. "23 — MISCELANEOS") y luego por
        código o descripción (texto libre, p.ej. "23" o "MISCELANEOS").
        """
        texto = self.causa_combo.currentText().strip()
        if not texto:
            return None
        for i in range(self.causa_combo.count()):
            if self.causa_combo.itemText(i).strip().lower() == texto.lower():
                return self.causa_combo.itemData(i)
        causa = LlantaService.buscar_causa_rechazo(texto)
        return causa.id if causa else None

    def _aplicar_cambio(self) -> bool:
        """Aplica el cambio de estado de la llanta encontrada. True si fue OK."""
        if not self._llanta_encontrada:
            QMessageBox.warning(self, "Validación", "No hay llanta seleccionada")
            return False
        causa_id = None
        if self.nuevo_estado == "RECHAZADA":
            causa_id = self._resolver_causa_id()
            if causa_id is None:
                QMessageBox.warning(
                    self,
                    "Validación",
                    "Para rechazar la llanta debe seleccionar una causa de "
                    "rechazo válida (número o texto)",
                )
                return False
        ok, msg = LlantaService.cambiar_estado(
            self._llanta_encontrada.id, self.nuevo_estado, causa_id
        )
        if ok:
            QMessageBox.information(self, "Éxito", msg)
            return True
        QMessageBox.warning(self, "Error", msg)
        return False

    def _cambiar_y_cerrar(self) -> None:
        """Aplica el cambio y cierra el formulario."""
        if self._aplicar_cambio():
            self.accept()

    def _cambio_rapido_aplicar(self) -> None:
        """Aplica el cambio y limpia el formulario para la siguiente llanta
        (el recuadro permanece abierto — inspección continua)."""
        if self._aplicar_cambio():
            self.tiquete_input.clear()
            self.info_label.setText("")
            self.info_label.setStyleSheet("color: #666;")
            self.estado_combo.setEnabled(False)
            self.guardar_btn.setEnabled(False)
            self.rapido_btn.setEnabled(False)
            self.causa_combo.setCurrentText("")
            self.causa_combo.setEnabled(False)
            self._llanta_encontrada = None
            self.tiquete_input.setFocus()

    def _buscar_llanta(self) -> None:
        tiquete = self.tiquete_input.text().strip()
        if not tiquete:
            self.info_label.setText("")
            self.estado_combo.setEnabled(False)
            self.guardar_btn.setEnabled(False)
            self.rapido_btn.setEnabled(False)
            self.causa_combo.setCurrentText("")
            self.causa_combo.setEnabled(False)
            self._llanta_encontrada = None
            return

        # La BD guarda el tiquete SIN el prefijo "J" (tiquete físico real, desde v2.8.14).
        # Se acepta también con "J" por compatibilidad con datos antiguos.
        try:
            with get_session() as s:
                llanta = LlantaRepository.get_by_tiquete(s, tiquete)
                if not llanta and not tiquete.startswith("J"):
                    llanta = LlantaRepository.get_by_tiquete(s, "J" + tiquete)
        except Exception as e:
            logger.error(
                "Error buscando llanta por tiquete %s: %s", tiquete, e, exc_info=True
            )
            self._llanta_encontrada = None
            self.info_label.setText("Error al buscar la llanta. Consulte el log.")
            self.info_label.setStyleSheet("color: #c62828;")
            self.estado_combo.setEnabled(False)
            self.guardar_btn.setEnabled(False)
            self.rapido_btn.setEnabled(False)
            self.causa_combo.setEnabled(False)
            return
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
            self.rapido_btn.setEnabled(True)
            self._actualizar_estado_causa()
        else:
            self.info_label.setText("✗ Llanta no encontrada")
            self.info_label.setStyleSheet("color: #c62828;")
            self.estado_combo.setEnabled(False)
            self.guardar_btn.setEnabled(False)
            self.rapido_btn.setEnabled(False)
            self.causa_combo.setCurrentText("")
            self.causa_combo.setEnabled(False)

    @property
    def llanta_encontrada(self) -> Llanta | None:
        return self._llanta_encontrada

    @property
    def nuevo_estado(self) -> str:
        return self.estado_combo.currentText()