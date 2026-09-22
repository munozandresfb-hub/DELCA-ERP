from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.finanzas.services.factura_service import FacturaService
from src.modules.finanzas.views.abonos_cliente_dialog import AbonosClienteDialog
from src.modules.usuarios.services.permiso_service import tiene_permiso_por_usuario


class CarteraView(QWidget):
    """Accounts receivable view with client balances and aging report."""

    def __init__(self, user=None) -> None:
        super().__init__()
        self.user = user
        self.setup_ui()
        try:
            self._cargar_datos()
        except Exception as e:
            print(f"[CarteraView] Error al cargar datos iniciales: {e}")

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # Header
        header = QLabel("Cartera")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px 0;"
        )
        layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addStretch()

        export_btn = QPushButton("📥 Exportar Cartera a Excel")
        export_btn.setStyleSheet(
            "background-color: #27ae60; color: white; padding: 8px 16px;"
            " border-radius: 4px; font-weight: 600;"
        )
        export_btn.clicked.connect(self._exportar_excel)
        toolbar.addWidget(export_btn)

        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self._cargar_datos)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)

        # Tabs
        self.tabs = QTabWidget()

        # Tab 1: Saldos por cliente
        self.clientes_tab = QWidget()
        self._setup_clientes_tab()
        self.tabs.addTab(self.clientes_tab, "Saldos por Cliente")

        # Tab 2: Antigüedad de saldos
        self.aging_tab = QWidget()
        self._setup_aging_tab()
        self.tabs.addTab(self.aging_tab, "Antigüedad de Saldos")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def _setup_clientes_tab(self) -> None:
        layout = QVBoxLayout()

        info = QLabel(
            "Clientes con saldo pendiente. Los saldos se actualizan "
            "automáticamente al crear facturas o registrar pagos."
        )
        info.setStyleSheet("color: #7f8c8d; font-size: 12px; padding: 4px 0;")
        layout.addWidget(info)

        cols = ["Cliente", "Celular", "Fecha de Generación", "Total Abonado", "Saldo Pendiente", "Fecha de Pago"]
        self.clientes_table = QTableWidget()
        self.clientes_table.setColumnCount(len(cols))
        self.clientes_table.setHorizontalHeaderLabels(cols)
        self.clientes_table.horizontalHeader().setStretchLastSection(True)
        self.clientes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.clientes_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.clientes_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.clientes_table.setAlternatingRowColors(True)
        self.clientes_table.cellClicked.connect(self._on_clientes_cell_clicked)

        layout.addWidget(self.clientes_table)
        self.clientes_tab.setLayout(layout)

    def _setup_aging_tab(self) -> None:
        layout = QVBoxLayout()

        # Summary badges
        summary_layout = QHBoxLayout()
        self._badges: dict[str, QLabel] = {}
        for rango, color in [
            ("0-30 días", "#2ecc71"),
            ("31-60 días", "#f39c12"),
            ("61-90 días", "#e67e22"),
            ("90+ días", "#e74c3c"),
        ]:
            badge = QLabel(f"{rango}: $0")
            badge.setStyleSheet(
                f"background-color: {color}20; color: {color}; "
                f"font-weight: 600; padding: 8px 16px; "
                f"border-radius: 8px; font-size: 13px;"
            )
            self._badges[rango] = badge
            summary_layout.addWidget(badge)
        summary_layout.addStretch()
        layout.addLayout(summary_layout)

        cols = [
            "Factura",
            "Cliente",
            "Celular",
            "Fecha",
            "Total",
            "Saldo",
            "DIAS DE MORA",
            "D\u00edas",
            "Rango",
        ]
        self.aging_table = QTableWidget()
        self.aging_table.setColumnCount(len(cols))
        self.aging_table.setHorizontalHeaderLabels(cols)
        self.aging_table.horizontalHeader().setStretchLastSection(True)
        self.aging_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.aging_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.aging_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.aging_table.setAlternatingRowColors(True)

        # Color rows by aging range
        self.aging_table.setStyleSheet(
            """
            QTableWidget::item { padding: 4px 8px; }
            """
        )

        layout.addWidget(self.aging_table)
        self.aging_tab.setLayout(layout)

    def _cargar_datos(self) -> None:
        self._cargar_clientes()
        self._cargar_aging()

    def _cargar_clientes(self) -> None:
        cartera = FacturaService.obtener_cartera_clientes()
        self._cartera = cartera
        self.clientes_table.setRowCount(len(cartera))

        for row, c in enumerate(cartera):
            self.clientes_table.setItem(
                row, 0, QTableWidgetItem(c["cliente_nombre"])
            )
            self.clientes_table.setItem(
                row, 1, QTableWidgetItem(c["cliente_celular"])
            )
            self.clientes_table.setItem(
                row, 2, QTableWidgetItem(c["fecha_ultima_factura"])
            )
            # Total Abonado (clickeable → ventana de abonos del cliente)
            abono_item = QTableWidgetItem(f"${c['total_abonado']:,.2f}")
            abono_item.setData(Qt.ItemDataRole.UserRole, c["cliente_id"])
            if c["total_abonado"] > 0:
                abono_item.setForeground(QColor("#2980b9"))
                abono_item.setToolTip("Click para ver detalle de abonos")
            self.clientes_table.setItem(row, 3, abono_item)
            self.clientes_table.setItem(
                row, 4, QTableWidgetItem(f"${c['saldo_pendiente']:,.2f}")
            )
            self.clientes_table.setItem(
                row, 5, QTableWidgetItem(c["fecha_pago"] or "—")
            )

            # Traffic light by days since last invoice (semáforo)
            dias = c.get("dias_ultima_factura", 0)
            color = "#2ecc71"  # verde
            if dias > 90:
                color = "#e74c3c"  # rojo
            elif dias > 60:
                color = "#e67e22"  # naranja
            elif dias > 30:
                color = "#f39c12"  # amarillo

            for col in range(self.clientes_table.columnCount()):
                item = self.clientes_table.item(row, col)
                if item:
                    item.setForeground(QColor(color))

    def _on_clientes_cell_clicked(self, row: int, col: int) -> None:
        """Click en 'Total Abonado' → ventana emergente de abonos (como en facturación)."""
        if col != 3:
            return
        cliente = self._cartera[row] if 0 <= row < len(self._cartera) else None
        if not cliente:
            return
        abonos = FacturaService.obtener_abonos_cliente(cliente["cliente_id"])
        dialog = AbonosClienteDialog(cliente["cliente_nombre"], abonos, self)
        dialog.exec()

    def _cargar_aging(self) -> None:
        aging = FacturaService.obtener_antiguedad_saldos()
        self.aging_table.setRowCount(len(aging))

        # Reset badges
        totals: dict[str, float] = {
            "0-30": 0,
            "31-60": 0,
            "61-90": 0,
            "90+": 0,
        }

        for row, a in enumerate(aging):
            self.aging_table.setItem(
                row, 0, QTableWidgetItem(a["numero"])
            )
            self.aging_table.setItem(
                row, 1, QTableWidgetItem(a["cliente_nombre"])
            )
            self.aging_table.setItem(
                row, 2, QTableWidgetItem(a["cliente_celular"])
            )
            self.aging_table.setItem(
                row, 3, QTableWidgetItem(a["fecha"])
            )
            self.aging_table.setItem(
                row, 4, QTableWidgetItem(f"${a['total']:,.2f}")
            )
            self.aging_table.setItem(
                row, 5, QTableWidgetItem(f"${a['saldo']:,.2f}")
            )
            self.aging_table.setItem(
                row, 6, QTableWidgetItem(str(a["dias_mora"]))
            )
            self.aging_table.setItem(
                row, 7, QTableWidgetItem(str(a["dias"]))
            )
            self.aging_table.setItem(
                row, 8, QTableWidgetItem(a["rango"])
            )

            # Color row based on age
            color = "#2ecc71"
            if a["dias"] > 90:
                color = "#e74c3c"
            elif a["dias"] > 60:
                color = "#e67e22"
            elif a["dias"] > 30:
                color = "#f39c12"

            for col in range(self.aging_table.columnCount()):
                item = self.aging_table.item(row, col)
                if item:
                    item.setForeground(QColor(color))

            # Accumulate for badges
            if a["dias"] <= 30:
                totals["0-30"] += a["saldo"]
            elif a["dias"] <= 60:
                totals["31-60"] += a["saldo"]
            elif a["dias"] <= 90:
                totals["61-90"] += a["saldo"]
            else:
                totals["90+"] += a["saldo"]

        # Update badges
        for rango_key, rango_label in [
            ("0-30", "0-30 días"),
            ("31-60", "31-60 días"),
            ("61-90", "61-90 días"),
            ("90+", "90+ días"),
        ]:
            badge = self._badges.get(rango_label)
            if badge:
                badge.setText(
                    f"{rango_label}: ${totals[rango_key]:,.2f}"
                )

    def _exportar_excel(self) -> None:
        if self.user and not tiene_permiso_por_usuario(self.user, "cartera.ver"):
            QMessageBox.warning(self, "Acceso Denegado", "No tiene permiso para exportar cartera")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Cartera a Excel",
            "cartera.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return

        ok, msg = FacturaService.exportar_cartera_excel(path)
        if ok:
            QMessageBox.information(self, "Exportación Exitosa", msg)
        else:
            QMessageBox.critical(self, "Error", msg)


