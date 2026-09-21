from typing import cast

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
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta
from src.modules.llantas.repositories.llanta_repository import LlantaRepository
from src.modules.llantas.services.llanta_service import (
    UBICACIONES_CAMBIO_MANUAL,
    UBICACIONES_DISPLAY,
    UBICACIONES_PLANTA,
    LlantaService,
)
from src.modules.llantas.services.llanta_service._core import (
    formatear_orden,
    formatear_tiquete,
)
from src.modules.llantas.viewmodels.llanta_viewmodel import LlantaViewModel
from sqlalchemy import func as sa_func


class _UbicacionRapidaDialog(QDialog):
    """Dialog to quickly change tire location by entering code.

    Ofrece siempre las opciones fijas de cambio manual: Cliente y Planta.
    La validación según el estado actual (reglas R1-R4, R6 del flujo
    correcto 2) la realiza el servicio.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cambio de Ubicación")
        self.resize(420, 200)
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

        self.ubicacion_combo = QComboBox()
        # Opciones fijas de cambio manual: Cliente, Planta
        for u in UBICACIONES_CAMBIO_MANUAL:
            self.ubicacion_combo.addItem(UBICACIONES_DISPLAY.get(u, u), u)
        self.ubicacion_combo.setEnabled(False)
        self.ubicacion_combo.setStyleSheet(
            "font-size: 14px; padding: 4px; border: 1px solid #ccc; border-radius: 4px;"
        )
        form.addRow("Nueva Ubicación:", self.ubicacion_combo)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.mover_btn = QPushButton("Mover")
        self.mover_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #2980b9; }"
            "QPushButton:disabled { background-color: #bdc3c7; }"
        )
        self.mover_btn.clicked.connect(self.accept)
        self.mover_btn.setEnabled(False)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.setStyleSheet(
            "QPushButton { background-color: #95a5a6; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #7f8c8d; }"
        )
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(self.mover_btn)
        btn_layout.addWidget(cancelar_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _buscar_llanta(self) -> None:
        tiquete = self.tiquete_input.text().strip()
        if not tiquete:
            self.info_label.setText("")
            self.ubicacion_combo.setEnabled(False)
            self.mover_btn.setEnabled(False)
            self._llanta_encontrada = None
            return

        # La BD guarda el tiquete SIN el prefijo "J" (tiquete físico real, desde v2.8.14).
        # Se acepta también con "J" por compatibilidad con datos antiguos.
        with get_session() as s:
            llanta = LlantaRepository.get_by_tiquete(s, tiquete)
            if not llanta and not tiquete.startswith("J"):
                llanta = LlantaRepository.get_by_tiquete(s, "J" + tiquete)
            ultima_ubicacion = (
                s.query(UbicacionLlanta)
                .filter(UbicacionLlanta.llanta_id == llanta.id)
                .order_by(UbicacionLlanta.fecha.desc())
                .first()
            ) if llanta else None
        self._llanta_encontrada = llanta
        if llanta:
            marca_text = llanta.marca_obj.nombre if llanta.marca_obj else (llanta.marca or "?")
            dimension_text = llanta.dimension_obj.display if llanta.dimension_obj else (llanta.dimension or "?")
            estado = llanta.estado or "PENDIENTE"
            ubic_actual = "N/A"
            if ultima_ubicacion:
                ubic_val = str(ultima_ubicacion.ubicacion)
                ubic_actual = UBICACIONES_DISPLAY.get(ubic_val, ubic_val)
            self.info_label.setText(
                f"  {marca_text} {dimension_text} — Estado: {estado} — "
                f"Ubicación: {ubic_actual}"
            )
            self.info_label.setStyleSheet("color: #2e7d32; font-size: 13px;")

            # Opciones fijas (Cliente, Planta) ya cargadas en setup_ui.
            # Preseleccionar la ubicación actual si está disponible.
            db_val = ultima_ubicacion.ubicacion if ultima_ubicacion else ""
            idx = self.ubicacion_combo.findData(db_val)
            if idx >= 0:
                self.ubicacion_combo.setCurrentIndex(idx)
            self.ubicacion_combo.setEnabled(True)
            self.mover_btn.setEnabled(True)
        else:
            self.info_label.setText("  Llanta no encontrada")
            self.info_label.setStyleSheet("color: #c62828; font-size: 13px;")
            self.ubicacion_combo.setEnabled(False)
            self.mover_btn.setEnabled(False)

    @property
    def llanta_encontrada(self) -> Llanta | None:
        return self._llanta_encontrada

    @property
    def nueva_ubicacion(self) -> str:
        return self.ubicacion_combo.currentData()


class PlantaView(QWidget):
    """Plant floor view - shows tire locations and allows moving them."""

    COLUMNAS = [
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
        try:
            self._cargar_datos()
        except Exception as e:
            print(f"[PlantaView] Error al cargar datos iniciales: {e}")

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # ── Header ─────────────────────────────────────────────────────
        header = QLabel("Planta - Ubicaciones")
        header.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #3498db; padding: 10px 0;"
        )
        layout.addWidget(header)

        # ── Filter row ─────────────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Ubicación:"))

        self.ubicacion_filter = QComboBox()
        self.ubicacion_filter.addItem("Todas", "")
        for u in UBICACIONES_PLANTA:
            display = UBICACIONES_DISPLAY.get(u, u)
            self.ubicacion_filter.addItem(display, u)
        self.ubicacion_filter.currentIndexChanged.connect(self._filtrar)
        self.ubicacion_filter.setStyleSheet(
            "QComboBox { font-size: 14px; padding: 4px 8px; border: 1px solid #ccc; "
            "border-radius: 4px; min-width: 200px; }"
        )
        filter_row.addWidget(self.ubicacion_filter)
        filter_row.addStretch()

        refresh_btn = QPushButton("Actualizar")
        refresh_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #2980b9; }"
        )
        refresh_btn.clicked.connect(self._cargar_datos)
        filter_row.addWidget(refresh_btn)

        layout.addLayout(filter_row)

        # ── Move controls ──────────────────────────────────────────────
        move_row = QHBoxLayout()
        move_row.addWidget(QLabel("Mover a:"))

        self.ubicacion_combo = QComboBox()
        for u in UBICACIONES_PLANTA:
            display = UBICACIONES_DISPLAY.get(u, u)
            self.ubicacion_combo.addItem(display, u)
        self.ubicacion_combo.setStyleSheet(
            "QComboBox { font-size: 14px; padding: 4px 8px; border: 1px solid #ccc; "
            "border-radius: 4px; min-width: 200px; }"
        )
        move_row.addWidget(self.ubicacion_combo)

        mover_btn = QPushButton("Mover")
        mover_btn.setStyleSheet(
            "QPushButton { background-color: #f39c12; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #e67e22; }"
        )
        mover_btn.clicked.connect(self._mover_ubicacion)
        move_row.addWidget(mover_btn)

        cambio_ubicacion_btn = QPushButton("CAMBIO DE UBICACIÓN")
        cambio_ubicacion_btn.setStyleSheet(
            "QPushButton { background-color: #9b59b6; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #8e44ad; }"
        )
        cambio_ubicacion_btn.clicked.connect(self._ubicacion_rapida)
        move_row.addWidget(cambio_ubicacion_btn)

        move_row.addStretch()
        layout.addLayout(move_row)

        # ── Pagination ─────────────────────────────────────────────────
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

        # ── Table ──────────────────────────────────────────────────────
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
        self.table.setStyleSheet(
            "QTableWidget { font-size: 13px; }"
            "QHeaderView::section { font-weight: bold; font-size: 13px; }"
        )

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _cargar_datos(self) -> None:
        self.viewmodel.cargar_llantas()
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
        self.viewmodel.cargar_llantas()
        ubicacion = self.ubicacion_filter.currentData()
        if ubicacion:
            # Filtrar por ubicación SIN cargar todo: busca solo en la página
            # actual por defecto (el filtro de estado/ubicación completo se
            # puede afinar con la búsqueda del módulo Llantas).
            ids_pagina = {l.id for l in self.viewmodel.llantas}
            with get_session() as session:
                ids_con_ubicacion = (
                    session.query(UbicacionLlanta.llanta_id)
                    .filter(
                        UbicacionLlanta.ubicacion == ubicacion,
                        UbicacionLlanta.llanta_id.in_(ids_pagina),
                    )
                    .distinct()
                    .all()
                )
                ids = {r[0] for r in ids_con_ubicacion}
            llantas = [l for l in self.viewmodel.llantas if l.id in ids]
        else:
            llantas = self.viewmodel.llantas
        self._poblar_tabla(llantas)

    def _poblar_tabla(
        self, llantas: list | None = None
    ) -> None:
        if llantas is None:
            llantas = self.viewmodel.llantas

        # Pre-cargar todas las últimas ubicaciones (evita N+1)
        ids = [l.id for l in llantas]
        ultimas_ubicaciones: dict[int, str] = {}
        if ids:
            with get_session() as session:
                subq = (
                    session.query(
                        UbicacionLlanta.llanta_id,
                        sa_func.max(UbicacionLlanta.fecha).label("max_fecha"),
                    )
                    .filter(UbicacionLlanta.llanta_id.in_(ids))
                    .group_by(UbicacionLlanta.llanta_id)
                    .subquery()
                )
                filas = (
                    session.query(UbicacionLlanta)
                    .join(
                        subq,
                        (UbicacionLlanta.llanta_id == subq.c.llanta_id)
                        & (UbicacionLlanta.fecha == subq.c.max_fecha),
                    )
                    .all()
                )
                for f in filas:
                    ultimas_ubicaciones[cast(int, f.llanta_id)] = str(f.ubicacion)

        self.table.setRowCount(len(llantas))

        for row, l in enumerate(llantas):
            # 0 - Cliente
            nombre_cliente = l.cliente.nombre if l.cliente else "—"
            self.table.setItem(row, 0, QTableWidgetItem(nombre_cliente))
            # 1 - Tiquete (sin el prefijo "J" de la serie)
            self.table.setItem(row, 1, QTableWidgetItem(formatear_tiquete(l.tiquete)))
            # 2 - N° Orden
            self.table.setItem(row, 2, QTableWidgetItem(formatear_orden(l.numero_orden, l.consecutivo) or "—"))
            # 3 - Dimensión (estandarizada)
            dim = l.dimension_obj.display if l.dimension_obj else (l.dimension or "—")
            self.table.setItem(row, 3, QTableWidgetItem(dim))
            # 4 - Diseño (estandarizado)
            dis = l.diseno_obj.nombre if l.diseno_obj else "—"
            self.table.setItem(row, 4, QTableWidgetItem(dis))
            # 5 - Estado
            self.table.setItem(row, 5, QTableWidgetItem(l.estado or ""))

            # 6 - Ubicación Actual (desde cache o fallback al campo del modelo)
            ubicacion_raw = (
                l.ubicacion_actual
                or ultimas_ubicaciones.get(l.id)
            )
            ubicacion_str = (
                UBICACIONES_DISPLAY.get(ubicacion_raw, ubicacion_raw)
                if ubicacion_raw
                else "N/A"
            )
            self.table.setItem(row, 6, QTableWidgetItem(ubicacion_str))

            # 7 - Fecha de Ingreso
            fecha = l.fecha_ingreso.strftime("%Y-%m-%d") if l.fecha_ingreso else "—"
            self.table.setItem(row, 7, QTableWidgetItem(fecha))

        self._actualizar_paginacion()

    def _mover_ubicacion(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Seleccionar",
                "Seleccione una llanta de la tabla",
            )
            return

        # Need the llanta ID: query by tiquete from the table
        tiquete = self.table.item(row, 1).text()
        with get_session() as s:
            llanta = LlantaRepository.get_by_tiquete(s, tiquete)
            if not llanta:
                QMessageBox.warning(self, "Error", "Llanta no encontrada")
                return
            llanta_id = llanta.id

        ubicacion = self.ubicacion_combo.currentData()

        ok, msg = self.viewmodel.mover_ubicacion(llanta_id, ubicacion)
        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _ubicacion_rapida(self) -> None:
        dialog = _UbicacionRapidaDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        llanta = dialog.llanta_encontrada
        if not llanta:
            return

        ok, msg = self.viewmodel.mover_ubicacion(
            llanta.id, dialog.nueva_ubicacion
        )
        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)
