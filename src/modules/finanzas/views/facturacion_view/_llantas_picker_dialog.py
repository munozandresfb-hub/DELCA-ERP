"""Diálogo emergente de precarga de llantas del cliente pendientes de facturación.

Muestra las llantas facturables del cliente seleccionado con: N° de orden
(con consecutivo), diseño, cliente y dimensión (más tiquete y precio del
catálogo). Permite seleccionar una o varias para agregarlas a la factura.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import logging

logger = logging.getLogger("delca.views")

from src.database.engine import get_session
from src.modules.finanzas.services.factura_service import FacturaService
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.services.costo_precio import costo_precio, indice_precios
from src.modules.llantas.services.llanta_service._core import (
    formatear_orden,
    formatear_tiquete,
)


class LlantasPickerDialog(QDialog):
    """Selección de llantas facturables del cliente (precarga).

    ``llantas_seleccionadas`` expone las Llanta marcadas al aceptar.
    """

    COLUMNAS = [
        "☑",
        "Tiquete",
        "N° Orden",
        "Diseño",
        "Cliente",
        "Dimensión",
        "Precio",
    ]

    def __init__(
        self, cliente_id: int, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Llantas a facturar")
        self.resize(820, 480)
        self._cliente_id = cliente_id
        self._llantas: list[Llanta] = []
        self._idx_precios: dict = {}
        self.setup_ui()
        self._cargar_llantas()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        try:
            with get_session() as s:
                self._idx_precios = indice_precios(s)
        except Exception as e:
            logger.error("Error cargando índice de precios: %s", e, exc_info=True)
            self._idx_precios = {}

        info = QLabel(
            "Seleccione las llantas del cliente pendientes de facturación:"
        )
        info.setStyleSheet("font-size: 13px; color: #7f8c8d; padding: 4px 0;")
        layout.addWidget(info)

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
            QTableWidget.SelectionMode.MultiSelection
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("QTableWidget { font-size: 13px; }")
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        agregar_btn = QPushButton("Agregar seleccionadas")
        agregar_btn.setStyleSheet(
            "QPushButton { background-color: #27ae60; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
            "QPushButton:hover { background-color: #219a52; }"
        )
        agregar_btn.clicked.connect(self._aceptar)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addWidget(agregar_btn)
        btn_layout.addWidget(cancelar_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _cargar_llantas(self) -> None:
        self._llantas = FacturaService.listar_llantas_facturables(
            cliente_id=self._cliente_id
        )
        self.table.setRowCount(len(self._llantas))

        for row, l in enumerate(self._llantas):
            # ☑
            check = QTableWidgetItem()
            check.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            check.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, check)
            # Tiquete
            self.table.setItem(
                row, 1, QTableWidgetItem(formatear_tiquete(l.tiquete))
            )
            # N° Orden (con consecutivo)
            orden = formatear_orden(l.numero_orden, l.consecutivo)
            self.table.setItem(row, 2, QTableWidgetItem(orden or "—"))
            # Diseño
            diseno = l.diseno_obj.nombre if l.diseno_obj else "—"
            self.table.setItem(row, 3, QTableWidgetItem(diseno))
            # Cliente
            nombre_cliente = l.cliente.nombre if l.cliente else "Sin cliente"
            self.table.setItem(row, 4, QTableWidgetItem(nombre_cliente))
            # Dimensión
            dim = (
                l.dimension_obj.display
                if l.dimension_obj
                else (l.dimension or "—")
            )
            self.table.setItem(row, 5, QTableWidgetItem(dim))
            # Precio (catálogo: normal → mínimo → 1 sin cobertura)
            precio = costo_precio(l, self._idx_precios)[1]
            self.table.setItem(row, 6, QTableWidgetItem(f"${precio:,.2f}"))

        if not self._llantas:
            self.table.setRowCount(1)
            item = QTableWidgetItem(
                "No hay llantas pendientes de facturación para este cliente"
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.table.setItem(0, 1, item)

    def _aceptar(self) -> None:
        seleccionadas: list[Llanta] = []
        for row in range(self.table.rowCount()):
            check_item = self.table.item(row, 0)
            if (
                check_item
                and check_item.checkState() == Qt.CheckState.Checked
                and row < len(self._llantas)
            ):
                seleccionadas.append(self._llantas[row])
        if not seleccionadas:
            QMessageBox.warning(
                self,
                "Validación",
                "Marque al menos una llanta para agregar",
            )
            return
        self._seleccionadas = seleccionadas
        self.accept()

    @property
    def llantas_seleccionadas(self) -> list[Llanta]:
        return getattr(self, "_seleccionadas", [])