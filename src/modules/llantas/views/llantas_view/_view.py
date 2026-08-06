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
from src.modules.llantas.services.tiquete_printer import TiquetePrinter
from src.modules.llantas.viewmodels.llanta_viewmodel import LlantaViewModel
from src.modules.llantas.views.catalogos_view import CatalogoMaestroDialog
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