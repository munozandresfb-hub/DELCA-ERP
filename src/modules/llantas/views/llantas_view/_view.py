from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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

from src.modules.llantas.services.llanta_service import (
    ESTADOS_PROCESO,
    UBICACIONES_DISPLAY,
    LlantaService,
)
from src.modules.llantas.services.llanta_service._core import (
    formatear_orden,
    formatear_tiquete,
)
from src.modules.llantas.services.tiquete_printer import TiquetePrinter
from src.modules.llantas.viewmodels.llanta_viewmodel import LlantaViewModel
from src.modules.usuarios.services.permiso_service import tiene_permiso_por_usuario
from src.modules.llantas.views.llantas_view._busqueda_avanzada_dialog import (
    BusquedaAvanzadaDialog,
)
from src.modules.llantas.views.llantas_view._dialogs import (
    CambioRapidoDialog,
    HistorialDialog,
    LlantaFormDialog,
)


class LlantasView(QWidget):
    """Full tire management view with table, filters and state control."""

    COLUMNAS = [
        "ID",  # hidden, used for row lookups
        "Cliente",
        "Tiquete",
        "N° Orden",
        "Dimensión",
        "Diseño",
        "Marca",
        "Estado",
        "Causa",
        "Ubicación Actual",
        "Fecha de Ingreso",
    ]

    def __init__(self, user=None) -> None:
        super().__init__()
        self.user = user
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

        cambio_rapido_btn = QPushButton("⚡ INSPECCION INICIAL")
        cambio_rapido_btn.clicked.connect(self._cambio_rapido)
        row2.addWidget(cambio_rapido_btn)

        historial_btn = QPushButton("Ver Historial")
        historial_btn.clicked.connect(self._ver_historial)
        row2.addWidget(historial_btn)

        imprimir_btn = QPushButton("🖨 Imprimir Tiquete")
        imprimir_btn.clicked.connect(self._imprimir_tiquete)
        row2.addWidget(imprimir_btn)

        editar_btn = QPushButton("✏️ EDITAR")
        editar_btn.setStyleSheet(
            "QPushButton { background: #2c3e50; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; border: none; }"
        )
        editar_btn.clicked.connect(self._editar_llanta)
        row2.addWidget(editar_btn)

        catalogos_btn = QPushButton("🔍 Búsqueda Avanzada")
        catalogos_btn.setStyleSheet(
            "QPushButton { background: #6c757d; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; border: none; }"
        )
        catalogos_btn.clicked.connect(self._busqueda_avanzada)
        row2.addWidget(catalogos_btn)

        # Eliminar llanta: SOLO para ADMIN (permiso llantas.eliminar)
        if self.user is not None and tiene_permiso_por_usuario(
            self.user, "llantas.eliminar"
        ):
            eliminar_btn = QPushButton("🗑 Eliminar")
            eliminar_btn.setStyleSheet(
                "QPushButton { background: #c0392b; color: white; font-weight: bold; "
                "padding: 6px 14px; border-radius: 4px; border: none; }"
            )
            eliminar_btn.clicked.connect(self._eliminar_llanta)
            row2.addWidget(eliminar_btn)

        layout.addLayout(row2)

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

    def _poblar_tabla(self) -> None:
        llantas = self.viewmodel.llantas
        self.table.setRowCount(len(llantas))

        for row, l in enumerate(llantas):
            self.table.setItem(row, 0, QTableWidgetItem(str(l.id)))
            nombre_cliente = l.cliente.nombre if l.cliente else "Sin cliente"
            self.table.setItem(row, 1, QTableWidgetItem(nombre_cliente))
            self.table.setItem(row, 2, QTableWidgetItem(formatear_tiquete(l.tiquete)))
            self.table.setItem(row, 3, QTableWidgetItem(formatear_orden(l.numero_orden, l.consecutivo) or "—"))
            dim = l.dimension_obj.display if l.dimension_obj else (l.dimension or "—")
            self.table.setItem(row, 4, QTableWidgetItem(dim))
            dis = l.diseno_obj.nombre if l.diseno_obj else "—"
            self.table.setItem(row, 5, QTableWidgetItem(dis))
            # Marca (del casco)
            marca = l.marca_obj.nombre if l.marca_obj else (l.marca or "—")
            self.table.setItem(row, 6, QTableWidgetItem(marca))
            self.table.setItem(row, 7, QTableWidgetItem(l.estado or ""))
            # Causa de rechazo (asignada en Inspección Inicial cuando RECHAZADA)
            causa = l.causa_rechazo
            causa_str = (
                f"{causa.codigo} — {causa.descripcion}" if causa else "—"
            )
            self.table.setItem(row, 8, QTableWidgetItem(causa_str))
            ubic_raw = l.ubicacion_actual or "—"
            ubic_str = (
                UBICACIONES_DISPLAY.get(ubic_raw, ubic_raw)
                if ubic_raw != "—"
                else "—"
            )
            self.table.setItem(row, 9, QTableWidgetItem(ubic_str))
            fecha = l.fecha_ingreso.strftime("%Y-%m-%d") if l.fecha_ingreso else "—"
            self.table.setItem(row, 10, QTableWidgetItem(fecha))

        self.table.setColumnHidden(0, True)
        self._actualizar_paginacion()

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
        tiquete_creado = data.get("tiquete")
        ok, msg = self.viewmodel.crear(**data)

        if ok:
            self._poblar_tabla()
            QMessageBox.information(self, "Éxito", msg)
            # Si el usuario pidió imprimir desde el formulario, imprime el
            # tiquete de la llanta recién creada (criterios de impresión intactos).
            if getattr(dialog, "imprimir", False) and tiquete_creado:
                llanta_nueva = self.viewmodel.obtener_por_tiquete(tiquete_creado)
                if llanta_nueva:
                    ok_imp, msg_imp = TiquetePrinter.print_tiquete(llanta_nueva, self)
                    if ok_imp:
                        QMessageBox.information(self, "Impresión", msg_imp)
                    else:
                        QMessageBox.warning(self, "Impresión", msg_imp)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _editar_llanta(self) -> None:
        """Edita la llanta seleccionada (cliente, diseño, orden...).
        El tiquete y el precio no se pueden modificar."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.viewmodel.llantas):
            QMessageBox.warning(
                self, "Validación", "Seleccione una llanta de la tabla"
            )
            return

        llanta = self.viewmodel.llantas[row]
        dialog = LlantaFormDialog(self, llanta=llanta)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        data = dialog.get_data()
        ok, msg = self.viewmodel.actualizar(llanta.id, **data)

        if ok:
            self._poblar_tabla()
            QMessageBox.information(self, "Éxito", msg)
            # Si el usuario pidió imprimir (disponible también al editar),
            # imprime el tiquete de la llanta editada.
            if getattr(dialog, "imprimir", False):
                llanta_editada = self.viewmodel.obtener_por_id(llanta.id)
                if llanta_editada:
                    ok_imp, msg_imp = TiquetePrinter.print_tiquete(llanta_editada, self)
                    if ok_imp:
                        QMessageBox.information(self, "Impresión", msg_imp)
                    else:
                        QMessageBox.warning(self, "Impresión", msg_imp)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _eliminar_llanta(self) -> None:
        """Elimina la llanta (tiquete) seleccionada. Solo ADMIN."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self.viewmodel.llantas):
            QMessageBox.information(
                self, "Seleccionar", "Seleccione una llanta de la tabla"
            )
            return
        llanta = self.viewmodel.llantas[row]
        confirm = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar la llanta con tiquete {formatear_tiquete(llanta.tiquete)}?\n\n"
            "Esta acción es IRREVERSIBLE y borra su historial de estados y "
            "ubicaciones.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok, msg = self.viewmodel.eliminar(llanta.id)
        if ok:
            self._poblar_tabla()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _cambio_rapido(self) -> None:
        # El diálogo aplica el cambio de estado (y permite inspección continua
        # con el botón "⚡ Cambio Rápido"). Al cerrar se RECARGA desde la BD
        # (el viewmodel cachea la lista; _poblar_tabla() sola mostraría los
        # estados viejos).
        dialog = CambioRapidoDialog(self)
        dialog.exec()
        self._cargar_datos()

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

    def _busqueda_avanzada(self) -> None:
        """Abre el diálogo de búsqueda avanzada y aplica los criterios elegidos
        (cliente, dimensión, diseño, estado y ubicación — combinados)."""
        dialog = BusquedaAvanzadaDialog(self)
        # "Limpiar": olvida la búsqueda y regenera toda la lista de llantas
        # (quita filtros avanzados y el término de la barra rápida).
        dialog.limpiar_solicitado.connect(self._limpiar_busqueda_avanzada)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        criterios = dialog.get_criterios()
        self.viewmodel.buscar_avanzada(**criterios)
        self._poblar_tabla()

    def _limpiar_busqueda_avanzada(self) -> None:
        """Olvida la búsqueda y regenera la lista completa de llantas."""
        self.viewmodel.limpiar_filtros_avanzados()
        self.search_input.clear()  # dispara _buscar con término vacío
        self._poblar_tabla()

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