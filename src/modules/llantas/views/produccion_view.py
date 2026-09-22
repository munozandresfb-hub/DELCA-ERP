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
    QVBoxLayout,
    QWidget,
)

from src.database.engine import get_session
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.repositories.llanta_repository import LlantaRepository
from src.modules.llantas.services.llanta_service import (
    DISENO_REPARADA,
    ESTADOS_INSPECCION_FINAL,
    ESTADOS_PROCESO,
    TRANSICIONES_VALIDAS,
    UBICACIONES_DISPLAY,
    VEREDICTOS_INSPECCION_FINAL,
    LlantaService,
)
from src.modules.llantas.services.llanta_service._core import (
    formatear_orden,
    formatear_tiquete,
)
from src.modules.llantas.viewmodels.llanta_viewmodel import LlantaViewModel


class _InspeccionFinalDialog(QDialog):
    """Dialog to apply final inspection quickly by entering the ticket number.

    Muestra la llanta encontrada y permite aplicar un veredicto de
    inspección (según "flujo correcto 2"). Solo se ofrecen los veredictos
    alcanzables desde el estado actual de la llanta.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Inspección Final")
        self.resize(460, 240)
        self._llanta_encontrada: Llanta | None = None
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        form = QFormLayout()

        self.tiquete_input = QLineEdit()
        self.tiquete_input.setPlaceholderText("Tiquete de la llanta...")
        self.tiquete_input.textChanged.connect(self._buscar_llanta)
        self.tiquete_input.setStyleSheet(
            "font-size: 14px; padding: 6px; border: 1px solid #ccc; border-radius: 4px;"
        )
        form.addRow("Tiquete:", self.tiquete_input)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #666; font-size: 13px;")
        form.addRow(self.info_label)

        # Veredictos: se cargan dinámicamente según el estado de la llanta
        # encontrada (solo las transiciones válidas del flujo).
        self.veredicto_combo = QComboBox()
        self.veredicto_combo.setEnabled(False)
        self.veredicto_combo.setStyleSheet(
            "font-size: 14px; padding: 4px; border: 1px solid #ccc; border-radius: 4px;"
        )
        form.addRow("Veredicto:", self.veredicto_combo)

        self.nota_rep = QLabel("")
        self.nota_rep.setStyleSheet("color: #e65100; font-size: 12px;")
        form.addRow(self.nota_rep)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.aplicar_btn = QPushButton("Aplicar")
        self.aplicar_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #229954; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.aplicar_btn.clicked.connect(self._aplicar_y_cerrar)
        self.aplicar_btn.setEnabled(False)

        # Cambio Rápido: aplica el veredicto y limpia para la siguiente llanta
        # sin cerrar el recuadro (inspección continua).
        self.rapido_btn = QPushButton("⚡ Cambio Rápido")
        self.rapido_btn.setStyleSheet(
            "QPushButton { background-color: #2c3e50; color: white; font-size: 13px; "
            "font-weight: bold; padding: 8px 16px; border-radius: 5px; border: none; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.rapido_btn.clicked.connect(self._cambio_rapido_aplicar)
        self.rapido_btn.setEnabled(False)

        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.setStyleSheet(
            "QPushButton { background-color: #95a5a6; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #7f8c8d; }"
        )
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.aplicar_btn)
        btn_layout.addWidget(self.rapido_btn)
        btn_layout.addWidget(cancelar_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _aplicar_operacion(self) -> bool:
        """Aplica el veredicto de inspección final. True si fue OK."""
        if not self._llanta_encontrada:
            QMessageBox.warning(self, "Validación", "No hay llanta seleccionada")
            return False
        ok, msg = LlantaService.aplicar_veredicto(
            self._llanta_encontrada.id, self.veredicto
        )
        if ok:
            QMessageBox.information(self, "Éxito", msg)
            return True
        QMessageBox.warning(self, "Error", msg)
        return False

    def _aplicar_y_cerrar(self) -> None:
        """Aplica el veredicto y cierra el formulario."""
        if self._aplicar_operacion():
            self.accept()

    def _cambio_rapido_aplicar(self) -> None:
        """Aplica el veredicto y limpia el formulario para la siguiente llanta
        (el recuadro permanece abierto — inspección continua)."""
        if self._aplicar_operacion():
            self.tiquete_input.clear()
            self.info_label.setText("")
            self.info_label.setStyleSheet("color: #666; font-size: 13px;")
            self.veredicto_combo.setEnabled(False)
            self.aplicar_btn.setEnabled(False)
            self.rapido_btn.setEnabled(False)
            self.nota_rep.setText("")
            self._llanta_encontrada = None
            self.tiquete_input.setFocus()

    def _buscar_llanta(self) -> None:
        tiquete = self.tiquete_input.text().strip()
        if not tiquete:
            self.info_label.setText("")
            self.veredicto_combo.clear()
            self.veredicto_combo.setEnabled(False)
            self.aplicar_btn.setEnabled(False)
            self.nota_rep.setText("")
            self._llanta_encontrada = None
            return

        # La BD guarda el tiquete SIN el prefijo "J" (tiquete físico real, desde v2.8.14).
        # Se acepta también con "J" por compatibilidad con datos antiguos.
        with get_session() as s:
            llanta = LlantaRepository.get_by_tiquete(s, tiquete)
            if not llanta and not tiquete.startswith("J"):
                llanta = LlantaRepository.get_by_tiquete(s, "J" + tiquete)
        self._llanta_encontrada = llanta
        if not llanta:
            self.info_label.setText("  Llanta no encontrada")
            self.info_label.setStyleSheet("color: #c62828; font-size: 13px;")
            self.veredicto_combo.clear()
            self.veredicto_combo.setEnabled(False)
            self.aplicar_btn.setEnabled(False)
            self.rapido_btn.setEnabled(False)
            self.nota_rep.setText("")
            return

        marca_text = (
            llanta.marca_obj.nombre if llanta.marca_obj else (llanta.marca or "?")
        )
        dimension_text = (
            llanta.dimension_obj.display
            if llanta.dimension_obj
            else (llanta.dimension or "?")
        )
        diseno_text = llanta.diseno_obj.nombre if llanta.diseno_obj else "—"
        estado = llanta.estado or "PENDIENTE"
        self.info_label.setText(
            f"  {marca_text} {dimension_text} — Diseño: {diseno_text} — "
            f"Estado: {estado}"
        )
        self.info_label.setStyleSheet("color: #2e7d32; font-size: 13px;")
        self.nota_rep.setText("")

        # Admisión: la inspección final aplica a llantas en estado
        # APTA/REENCAUCHADA/REPROCESO — CUALQUIER diseño de banda.
        if estado not in ESTADOS_INSPECCION_FINAL:
            self.info_label.setText(
                f"  ✗ Inspección final aplica a llantas en estado "
                f"{', '.join(ESTADOS_INSPECCION_FINAL)} (actual: {estado})"
            )
            self.info_label.setStyleSheet("color: #c62828; font-size: 13px;")
            self.veredicto_combo.clear()
            self.veredicto_combo.setEnabled(False)
            self.aplicar_btn.setEnabled(False)
            self.rapido_btn.setEnabled(False)
            return

        # Regla R5 (validada por el servicio): REPARADA solo con diseño REP.
        # El formulario admite cualquier diseño; se avisa por si el usuario
        # elige REPARADA en una llanta sin diseño REP (el servicio la rechaza).
        if diseno_text != DISENO_REPARADA:
            self.nota_rep.setText(
                f"  Reparada requiere diseño '{DISENO_REPARADA}' "
                f"(diseño actual: {diseno_text})"
            )
        else:
            self.nota_rep.setText("")

        # Veredictos alcanzables desde el estado actual (fix: se recargan en
        # cada búsqueda — antes quedaba vacío tras una búsqueda fallida).
        permitidos = TRANSICIONES_VALIDAS.get(estado, set())
        self.veredicto_combo.clear()
        for v in VEREDICTOS_INSPECCION_FINAL:
            if v in permitidos:
                self.veredicto_combo.addItem(v, v)
        if self.veredicto_combo.count() == 1:
            self.veredicto_combo.setCurrentIndex(0)

        self.veredicto_combo.setEnabled(True)
        self.aplicar_btn.setEnabled(True)
        self.rapido_btn.setEnabled(True)

    @property
    def llanta_encontrada(self) -> Llanta | None:
        return self._llanta_encontrada

    @property
    def veredicto(self) -> str:
        return self.veredicto_combo.currentData()


class ProduccionView(QWidget):
    """Production flow view - shows tires in production pipeline."""

    COLUMNAS = [
        "Cliente",
        "Tiquete",
        "N° Orden",
        "Dimensión",
        "Marca",
        "Diseño",
        "Estado",
        "Ubicación Actual",
        "Fecha de Ingreso",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.viewmodel = LlantaViewModel()
        self.setup_ui()
        try:
            self._cargar_datos()
        except Exception as e:
            print(f"[ProduccionView] Error al cargar datos iniciales: {e}")

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        header = QLabel("Flujo de Producción")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px 0;"
        )
        layout.addWidget(header)

        # Filter by state
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtrar por estado:"))

        self.estado_filter = QComboBox()
        self.estado_filter.addItem("Todos en producción", "")
        for est in ESTADOS_PROCESO:
            self.estado_filter.addItem(est, est)
        self.estado_filter.currentIndexChanged.connect(self._filtrar)
        filter_row.addWidget(self.estado_filter)

        refresh_btn = QPushButton("Actualizar")
        refresh_btn.clicked.connect(self._cargar_datos)
        filter_row.addWidget(refresh_btn)

        # Inspección final rápida (flujo correcto 2)
        inspeccion_btn = QPushButton("INSPECCIÓN FINAL")
        inspeccion_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #229954; }"
        )
        inspeccion_btn.clicked.connect(self._inspeccion_final)
        filter_row.addWidget(inspeccion_btn)

        filter_row.addStretch()

        layout.addLayout(filter_row)

        # Pagination row
        pag_row = QHBoxLayout()
        self.prev_btn = QPushButton("← Anterior")
        self.prev_btn.clicked.connect(self._pagina_anterior)
        self.prev_btn.setEnabled(False)
        pag_row.addWidget(self.prev_btn)

        self.pag_label = QLabel("")
        pag_row.addWidget(self.pag_label)

        self.next_btn = QPushButton("Siguiente →")
        self.next_btn.clicked.connect(self._pagina_siguiente)
        self.next_btn.setEnabled(False)
        pag_row.addWidget(self.next_btn)

        pag_row.addStretch()
        layout.addLayout(pag_row)

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
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _cargar_datos(self) -> None:
        estado = self.estado_filter.currentData()
        self.viewmodel.filtrar_por_estado(estado or None)
        self._poblar_tabla()

    def _pagina_anterior(self) -> None:
        self.viewmodel.pagina_anterior()
        self._poblar_tabla()

    def _pagina_siguiente(self) -> None:
        self.viewmodel.siguiente_pagina()
        self._poblar_tabla()

    def _actualizar_paginacion(self) -> None:
        vm = self.viewmodel
        self.prev_btn.setEnabled(vm.pagina > 0)
        self.next_btn.setEnabled(vm.hay_mas)
        desde = vm.pagina * vm.PAGE_SIZE + 1
        hasta = min((vm.pagina + 1) * vm.PAGE_SIZE, vm.total)
        self.pag_label.setText(
            f"Mostrando {desde}–{hasta} de {vm.total} llantas "
            f"(página {vm.pagina + 1})"
        )

    def _filtrar(self) -> None:
        self._cargar_datos()

    def _inspeccion_final(self) -> None:
        """Abre el diálogo de inspección final rápida por tiquete.

        El diálogo aplica el veredicto (y permite inspección continua con el
        botón "⚡ Cambio Rápido"). Al cerrar se refresca la tabla.
        """
        dialog = _InspeccionFinalDialog(self)
        dialog.exec()
        self._cargar_datos()

    def _poblar_tabla(self) -> None:
        llantas = self.viewmodel.llantas

        self.table.setRowCount(len(llantas))

        for row, l in enumerate(llantas):
            # Cliente
            nombre_cliente = l.cliente.nombre if l.cliente else "Sin cliente"
            self.table.setItem(row, 0, QTableWidgetItem(nombre_cliente))
            # Tiquete (sin el prefijo "J" de la serie)
            self.table.setItem(row, 1, QTableWidgetItem(formatear_tiquete(l.tiquete)))
            # N° Orden
            self.table.setItem(row, 2, QTableWidgetItem(formatear_orden(l.numero_orden, l.consecutivo) or "—"))
            # Dimensión (estandarizada desde catálogo)
            dim = l.dimension_obj.display if l.dimension_obj else (l.dimension or "—")
            self.table.setItem(row, 3, QTableWidgetItem(dim))
            # Marca (del casco)
            marca = l.marca_obj.nombre if l.marca_obj else (l.marca or "—")
            self.table.setItem(row, 4, QTableWidgetItem(marca))
            # Diseño (estandarizado desde catálogo)
            dis = l.diseno_obj.nombre if l.diseno_obj else "—"
            self.table.setItem(row, 5, QTableWidgetItem(dis))
            # Estado
            self.table.setItem(row, 6, QTableWidgetItem(l.estado or ""))
            # Ubicación Actual
            ubic_raw = l.ubicacion_actual or "—"
            ubic_str = (
                UBICACIONES_DISPLAY.get(ubic_raw, ubic_raw)
                if ubic_raw != "—"
                else "—"
            )
            self.table.setItem(row, 7, QTableWidgetItem(ubic_str))
            # Fecha de Ingreso
            fecha = l.fecha_ingreso.strftime("%Y-%m-%d") if l.fecha_ingreso else "—"
            self.table.setItem(row, 8, QTableWidgetItem(fecha))

        self._actualizar_paginacion()
