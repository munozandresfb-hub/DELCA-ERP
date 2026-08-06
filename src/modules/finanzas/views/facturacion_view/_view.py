from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
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

from src.modules.clientes.services.cliente_service import ClienteService
from src.modules.finanzas.models.factura_model import Factura
from src.modules.finanzas.services.factura_service import FacturaService
from src.modules.finanzas.views.facturacion_view._abonos_dialog import AbonosDialog
from src.modules.finanzas.views.facturacion_view._factura_form_dialog import (
    FacturaFormDialog,
)
from src.modules.finanzas.views.facturacion_view._pago_dialog import PagoDialog
from src.modules.inventario.views.precios_view import PreciosDisenoDialog


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