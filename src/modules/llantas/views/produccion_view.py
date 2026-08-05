from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.services.llanta_service import (
    ESTADOS_PROCESO,
    UBICACIONES_DISPLAY,
)
from src.modules.llantas.viewmodels.llanta_viewmodel import LlantaViewModel


class ProduccionView(QWidget):
    """Production flow view - shows tires in production pipeline."""

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

        layout.addLayout(filter_row)

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

    def _filtrar(self) -> None:
        self._cargar_datos()

    def _poblar_tabla(self) -> None:
        llantas = self.viewmodel.llantas

        self.table.setRowCount(len(llantas))

        for row, l in enumerate(llantas):
            # Cliente
            nombre_cliente = l.cliente.nombre if l.cliente else "Sin cliente"
            self.table.setItem(row, 0, QTableWidgetItem(nombre_cliente))
            # Tiquete
            self.table.setItem(row, 1, QTableWidgetItem(l.tiquete or ""))
            # N° Orden
            self.table.setItem(row, 2, QTableWidgetItem(l.numero_orden or "—"))
            # Dimensión (estandarizada desde catálogo)
            dim = l.dimension_obj.display if l.dimension_obj else (l.dimension or "—")
            self.table.setItem(row, 3, QTableWidgetItem(dim))
            # Diseño (estandarizado desde catálogo)
            dis = l.diseno_obj.nombre if l.diseno_obj else "—"
            self.table.setItem(row, 4, QTableWidgetItem(dis))
            # Estado
            self.table.setItem(row, 5, QTableWidgetItem(l.estado or ""))
            # Ubicación Actual
            ubic_raw = l.ubicacion_actual or "—"
            ubic_str = (
                UBICACIONES_DISPLAY.get(ubic_raw, ubic_raw)
                if ubic_raw != "—"
                else "—"
            )
            self.table.setItem(row, 6, QTableWidgetItem(ubic_str))
            # Fecha de Ingreso
            fecha = l.fecha_ingreso.strftime("%Y-%m-%d") if l.fecha_ingreso else "—"
            self.table.setItem(row, 7, QTableWidgetItem(fecha))
