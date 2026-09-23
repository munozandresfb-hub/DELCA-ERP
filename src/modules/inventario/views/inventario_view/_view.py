"""Vista principal de inventario: KPIs, materia prima, llantas terminadas."""

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.inventario.models.producto_model import Producto
from src.modules.inventario.services.inventario_kpi_service import InventarioKpiService
from src.modules.inventario.services.producto_service import ProductoService
from src.modules.inventario.views.inventario_view._config_dialog import (
    ConfiguracionInventarioDialog,
)
from src.modules.inventario.views.inventario_view._documento_dialogs import (
    _DocumentoSearchDialog,
)
from src.modules.inventario.views.inventario_view._producto_mp_dialog import (
    _CrearProductoDialog,
)
from src.modules.inventario.views.inventario_view._widgets import (
    C_AMBAR,
    C_AZUL,
    C_ROJO,
    C_VERDE,
    _KpiCard,
    _color_antiguedad,
)


class InventarioView(QWidget):
    """Inventory dashboard with KPIs, raw materials, and finished tires."""

    COLUMNAS_MP = [
        "ID", "SKU", "Nombre", "Categoría", "Cantidad UND", "Unidad",
        "Q minima en planta", "Cantidad KG", "Costo/KG", "Valor Total",
    ]
    COLUMNAS_CONSUMIBLES = [
        "ID", "SKU", "Nombre", "Categoría", "Cantidad UND", "Unidad",
        "Q minima en planta", "Cantidad KG", "Costo/KG", "Valor Total",
    ]
    COLUMNAS_TERMINADAS = [
        "ID", "Tiquete", "Diseño", "Dimensión", "Costo Fabr.",
        "Precio Vta.", "Margen", "Cliente", "Días en Planta",
    ]

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout()

        # Header
        header = QLabel("📦 Inventario")
        header.setStyleSheet(
            "font-size: 20px; font-weight: bold; padding: 8px 0;"
        )
        layout.addWidget(header)

        # KPI cards
        kpi_row = QHBoxLayout()
        self._kpi_widgets: dict[str, _KpiCard] = {}
        kpi_defs = [
            ("mp", "MP Disponible", "0", C_AZUL, "Rollos de banda en planta (materia prima)"),
            ("valor", "Valor Inventario", "$0", C_AZUL, "Valor total del inventario de MP"),
            ("capacidad", "Capacidad Prod.", "0 und", C_VERDE,
             "Llantas estimadas producibles con MP actual"),
            ("planta", "En Planta", "0 und", C_AMBAR,
             "Llantas terminadas sin retirar"),
            ("margen", "Margen Potencial", "$0", C_AMBAR,
             "Margen bruto si se venden todas las llantas en planta"),
        ]
        for key, titulo, valor, color, tooltip in kpi_defs:
            card = _KpiCard(titulo, valor, color, tooltip)
            self._kpi_widgets[key] = card
            kpi_row.addWidget(card)
        layout.addLayout(kpi_row)

        # ── Toolbar ─────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        btn_nuevo_mp = QPushButton("🧾 Nuevo Producto")
        btn_nuevo_mp.setStyleSheet(
            f"QPushButton {{ background: {C_AZUL}; color: white; font-weight: bold; "
            f"padding: 8px 18px; border-radius: 5px; border: none; }}"
        )
        btn_nuevo_mp.clicked.connect(self._nuevo_producto_mp)

        btn_docs = QPushButton("📋 Historial MP")
        btn_docs.setStyleSheet(
            "QPushButton { background: #6c757d; color: white; font-weight: bold; "
            "padding: 8px 18px; border-radius: 5px; border: none; }"
        )
        btn_docs.clicked.connect(self._abrir_documentos)

        btn_config = QPushButton("⚙️ Precios y Config")
        btn_config.setStyleSheet(
            "QPushButton { background: #6c757d; color: white; font-weight: bold; "
            "padding: 8px 18px; border-radius: 5px; border: none; }"
        )
        btn_config.clicked.connect(self._abrir_config)

        self.btn_reportes = QPushButton("📊 Reportes ▾")
        self.btn_reportes.setStyleSheet(
            "QPushButton { background: #495057; color: white; font-weight: bold; "
            "padding: 8px 18px; border-radius: 5px; border: none; }"
        )
        self._menu_reportes = QMenu()
        self._menu_reportes.addAction("Reencauchadas esta semana", self._reporte_semanal)
        self._menu_reportes.addAction("1 mes en planta (≥30 días)", self._reporte_1mes)
        self._menu_reportes.addAction("3 meses en planta (≥90 días)", self._reporte_3meses)
        self._menu_reportes.addAction("6 meses en planta (≥180 días)", self._reporte_6meses)
        self._menu_reportes.addAction("12 meses en planta (≥365 días)", self._reporte_12meses)
        self._menu_reportes.addSeparator()
        self._menu_reportes.addAction("📄 MP — Stock general", self._reporte_mp_stock)
        self._menu_reportes.addAction("📄 MP — Punto de reorden (bajo mínimo)", self._reporte_mp_reorden)
        self._menu_reportes.addSeparator()
        self._menu_reportes.addAction("📄 Consumibles — Stock general", self._reporte_cons_stock)
        self._menu_reportes.addAction("📄 Consumibles — Punto de reorden", self._reporte_cons_reorden)
        self._menu_reportes.addSeparator()
        self._menu_reportes.addAction("Exportar tabla a Excel (simulado)", self._exportar_excel)
        self.btn_reportes.setMenu(self._menu_reportes)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setStyleSheet(
            "QPushButton { font-size: 16px; padding: 8px 14px; border-radius: 5px; "
            "border: 1px solid #ccc; }"
        )
        btn_refresh.clicked.connect(self._refresh_all)

        toolbar.addWidget(btn_nuevo_mp)
        toolbar.addWidget(btn_docs)
        toolbar.addStretch()
        toolbar.addWidget(btn_config)
        toolbar.addWidget(self.btn_reportes)
        toolbar.addWidget(btn_refresh)
        layout.addLayout(toolbar)

        # ── Tabs ────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #ddd; border-top: none; }"
        )

        # Tab 1: Materia Prima
        self.tab_mp = QWidget()
        mp_layout = QVBoxLayout()
        mp_layout.setContentsMargins(0, 0, 0, 0)

        mp_filter_row = QHBoxLayout()
        self.mp_busqueda = QLineEdit()
        self.mp_busqueda.setPlaceholderText("Buscar por nombre, SKU...")
        self.mp_busqueda.setStyleSheet("font-size: 13px; padding: 5px; max-width: 300px;")
        self.mp_busqueda.textChanged.connect(self._filtrar_mp)
        mp_filter_row.addWidget(self.mp_busqueda)
        mp_filter_row.addStretch()
        mp_layout.addLayout(mp_filter_row)

        self.tabla_mp = QTableWidget()
        self.tabla_mp.setColumnCount(len(self.COLUMNAS_MP))
        self.tabla_mp.setHorizontalHeaderLabels(self.COLUMNAS_MP)
        self.tabla_mp.horizontalHeader().setStretchLastSection(True)
        self.tabla_mp.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_mp.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_mp.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_mp.setAlternatingRowColors(True)
        self.tabla_mp.setColumnHidden(0, True)
        mp_layout.addWidget(self.tabla_mp)
        self.tab_mp.setLayout(mp_layout)
        self.tabs.addTab(self.tab_mp, "Materia Prima")

        # Tab 2: Llantas Terminadas
        self.tab_term = QWidget()
        term_layout = QVBoxLayout()
        term_layout.setContentsMargins(0, 0, 0, 0)

        self.term_busqueda = QLineEdit()
        self.term_busqueda.setPlaceholderText("Buscar por código, cliente...")
        self.term_busqueda.setStyleSheet("font-size: 13px; padding: 5px; max-width: 300px;")
        self.term_busqueda.textChanged.connect(self._filtrar_terminadas)
        term_layout.addWidget(self.term_busqueda)

        self.tabla_term = QTableWidget()
        self.tabla_term.setColumnCount(len(self.COLUMNAS_TERMINADAS))
        self.tabla_term.setHorizontalHeaderLabels(self.COLUMNAS_TERMINADAS)
        self.tabla_term.horizontalHeader().setStretchLastSection(True)
        self.tabla_term.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_term.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_term.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_term.setAlternatingRowColors(True)
        self.tabla_term.setColumnHidden(0, True)
        term_layout.addWidget(self.tabla_term)
        self.tab_term.setLayout(term_layout)
        self.tabs.addTab(self.tab_term, "Llantas Terminadas")

        # Tab 3: Consumibles
        self.tab_cons = QWidget()
        cons_layout = QVBoxLayout()
        cons_layout.setContentsMargins(0, 0, 0, 0)

        self.cons_busqueda = QLineEdit()
        self.cons_busqueda.setPlaceholderText("Buscar por nombre, SKU...")
        self.cons_busqueda.setStyleSheet("font-size: 13px; padding: 5px; max-width: 300px;")
        self.cons_busqueda.textChanged.connect(self._filtrar_consumibles)
        cons_layout.addWidget(self.cons_busqueda)

        self.tabla_cons = QTableWidget()
        self.tabla_cons.setColumnCount(len(self.COLUMNAS_CONSUMIBLES))
        self.tabla_cons.setHorizontalHeaderLabels(self.COLUMNAS_CONSUMIBLES)
        self.tabla_cons.horizontalHeader().setStretchLastSection(True)
        self.tabla_cons.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_cons.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_cons.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_cons.setAlternatingRowColors(True)
        self.tabla_cons.setColumnHidden(0, True)
        cons_layout.addWidget(self.tabla_cons)
        self.tab_cons.setLayout(cons_layout)
        self.tabs.addTab(self.tab_cons, "Consumibles")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        # Data cache
        self._mp_cache: list[Producto] = []
        self._term_cache: list[dict] = []
        self._cons_cache: list[Producto] = []

        # Initial load
        QTimer.singleShot(0, self._refresh_all)

    # ── Refresh ─────────────────────────────────────────────────────

    def _refresh_all(self) -> None:
        try:
            self._cargar_kpis()
        except Exception as e:
            print(f"[InventarioView] Error cargando KPIs: {e}")
        try:
            self._cargar_mp()
        except Exception as e:
            print(f"[InventarioView] Error cargando MP: {e}")
        try:
            self._cargar_terminadas()
        except Exception as e:
            print(f"[InventarioView] Error cargando terminadas: {e}")
        try:
            self._cargar_consumibles()
        except Exception as e:
            print(f"[InventarioView] Error cargando consumibles: {e}")

    def _cargar_kpis(self) -> None:
        kpis = InventarioKpiService.resumen_kpis()
        self._kpi_widgets["mp"].actualizar(f"{kpis['mp_disponible']} rollos")
        self._kpi_widgets["valor"].actualizar(f"${kpis['valor_inventario']:,.0f}")
        self._kpi_widgets["capacidad"].actualizar(f"{kpis['capacidad_prod']} und")
        self._kpi_widgets["planta"].actualizar(f"{kpis['llantas_en_planta']} und")
        self._kpi_widgets["margen"].actualizar(f"${kpis['margen_potencial']:,.0f}")

    # ── Materia Prima ───────────────────────────────────────────────

    def _cargar_mp(self) -> None:
        self._mp_cache = InventarioKpiService.materias_primas()
        self._poblar_tabla_mp(self._mp_cache)

    def _poblar_tabla_mp(self, productos: list[Producto]) -> None:
        self.tabla_mp.setRowCount(len(productos))
        for row, p in enumerate(productos):
            stock = float(p.stock or 0)
            stock_kg = float(p.stock_kg or 0)
            minimo = float(p.stock_minimo or 0)
            costo = float(p.costo_unitario or 0)
            valor = ProductoService.valor_inventario_producto(p)
            self.tabla_mp.setItem(row, 0, QTableWidgetItem(str(p.id)))            # ID (hidden)
            self.tabla_mp.setItem(row, 1, QTableWidgetItem(p.sku or ""))           # SKU
            self.tabla_mp.setItem(row, 2, QTableWidgetItem(p.nombre or ""))        # Nombre
            self.tabla_mp.setItem(row, 3, QTableWidgetItem(p.categoria or ""))     # Categoría
            self.tabla_mp.setItem(row, 4, QTableWidgetItem(f"{stock:,.2f}"))       # Cantidad UND
            self.tabla_mp.setItem(row, 5, QTableWidgetItem(p.unidad_medida or "")) # Unidad
            self.tabla_mp.setItem(row, 6, QTableWidgetItem(f"{minimo:,.2f}"))      # Q minima en planta
            self.tabla_mp.setItem(row, 7, QTableWidgetItem(f"{stock_kg:,.2f}"))    # Cantidad KG
            self.tabla_mp.setItem(
                row, 8, QTableWidgetItem(f"${costo:,.2f}")                         # Costo Unit.
            )
            self.tabla_mp.setItem(
                row, 9, QTableWidgetItem(f"${valor:,.2f}")                         # Valor Total
            )

    def _filtrar_mp(self) -> None:
        term = self.mp_busqueda.text().strip().lower()
        if not term:
            self._poblar_tabla_mp(self._mp_cache)
            return
        filtrados = [
            p for p in self._mp_cache
            if term in (p.nombre or "").lower()
            or term in (p.sku or "").lower()
        ]
        self._poblar_tabla_mp(filtrados)

    # ── Consumibles ────────────────────────────────────────────────

    def _cargar_consumibles(self) -> None:
        self._cons_cache = InventarioKpiService.consumibles()
        self._poblar_tabla_consumibles(self._cons_cache)

    def _poblar_tabla_consumibles(self, productos: list[Producto]) -> None:
        self.tabla_cons.setRowCount(len(productos))
        for row, p in enumerate(productos):
            stock = float(p.stock or 0)
            stock_kg = float(p.stock_kg or 0)
            minimo = float(p.stock_minimo or 0)
            costo = float(p.costo_unitario or 0)
            valor = ProductoService.valor_inventario_producto(p)
            self.tabla_cons.setItem(row, 0, QTableWidgetItem(str(p.id)))            # ID (hidden)
            self.tabla_cons.setItem(row, 1, QTableWidgetItem(p.sku or ""))           # SKU
            self.tabla_cons.setItem(row, 2, QTableWidgetItem(p.nombre or ""))        # Nombre
            self.tabla_cons.setItem(row, 3, QTableWidgetItem(p.categoria or ""))     # Categoría
            self.tabla_cons.setItem(row, 4, QTableWidgetItem(f"{stock:,.2f}"))       # Cantidad UND
            self.tabla_cons.setItem(row, 5, QTableWidgetItem(p.unidad_medida or "")) # Unidad
            self.tabla_cons.setItem(row, 6, QTableWidgetItem(f"{minimo:,.2f}"))      # Q minima en planta
            self.tabla_cons.setItem(row, 7, QTableWidgetItem(f"{stock_kg:,.2f}"))    # Cantidad KG
            self.tabla_cons.setItem(
                row, 8, QTableWidgetItem(f"${costo:,.2f}")                           # Costo Unit.
            )
            self.tabla_cons.setItem(
                row, 9, QTableWidgetItem(f"${valor:,.2f}")                           # Valor Total
            )

    def _filtrar_consumibles(self) -> None:
        term = self.cons_busqueda.text().strip().lower()
        if not term:
            self._poblar_tabla_consumibles(self._cons_cache)
            return
        filtrados = [
            p for p in self._cons_cache
            if term in (p.nombre or "").lower()
            or term in (p.sku or "").lower()
        ]
        self._poblar_tabla_consumibles(filtrados)

    # ── Llantas Terminadas ──────────────────────────────────────────

    def _cargar_terminadas(self) -> None:
        self._term_cache = InventarioKpiService.terminadas_en_planta()
        self._poblar_tabla_term(self._term_cache)

    def _poblar_tabla_term(self, llantas: list[dict]) -> None:
        self.tabla_term.setRowCount(len(llantas))
        for row, ll in enumerate(llantas):
            self.tabla_term.setItem(row, 0, QTableWidgetItem(str(ll["id"])))
            self.tabla_term.setItem(row, 1, QTableWidgetItem(ll["tiquete"]))
            self.tabla_term.setItem(row, 2, QTableWidgetItem(ll["diseno"]))
            self.tabla_term.setItem(row, 3, QTableWidgetItem(ll["dimension"]))
            self.tabla_term.setItem(
                row, 4, QTableWidgetItem(f"${ll['costo_produccion']:,.0f}")
            )
            self.tabla_term.setItem(
                row, 5, QTableWidgetItem(f"${ll['precio_venta']:,.0f}")
            )
            margen = ll["margen"]
            margen_str = f"${margen:,.0f}"
            if margen >= 0:
                margen_str = f"+{margen_str}"
            item_margen = QTableWidgetItem(margen_str)
            item_margen.setForeground(QColor(C_VERDE) if margen >= 0 else QColor(C_ROJO))
            self.tabla_term.setItem(row, 6, item_margen)
            self.tabla_term.setItem(row, 7, QTableWidgetItem(ll["cliente"]))
            self.tabla_term.setItem(
                row, 8, QTableWidgetItem(str(ll["dias_en_planta"]))
            )

            # Color differential SOLO en la celda "Días en Planta" (la fila
            # mantiene los colores estándar del resto de módulos). El texto
            # queda en color oscuro para que el número siga siendo legible.
            color = _color_antiguedad(ll["dias_en_planta"])
            if color:
                item_dias = self.tabla_term.item(row, 8)
                if item_dias is not None:
                    item_dias.setBackground(color)
                    item_dias.setForeground(QColor("#2c2c2c"))

    def _filtrar_terminadas(self) -> None:
        term = self.term_busqueda.text().strip().lower()
        if not term:
            self._poblar_tabla_term(self._term_cache)
            return
        filtrados = [
            ll for ll in self._term_cache
            if term in (ll["tiquete"] or "").lower()
            or term in (ll["cliente"] or "").lower()
        ]
        self._poblar_tabla_term(filtrados)

    # ── Actions ─────────────────────────────────────────────────────

    def _nuevo_producto_mp(self) -> None:
        """Quick-create a raw material or consumible product."""
        dlg = _CrearProductoDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_all()

    def _abrir_documentos(self) -> None:
        """Open document search dialog."""
        dlg = _DocumentoSearchDialog(self)
        dlg.exec()

    def _abrir_config(self) -> None:
        dlg = ConfiguracionInventarioDialog(self)
        dlg.exec()

    # ── Reports ─────────────────────────────────────────────────────

    def _reporte_semanal(self) -> None:
        hoy = datetime.now()
        inicio = hoy - timedelta(days=7)
        datos = InventarioKpiService.reporte_semanal(inicio, hoy)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte Semanal",
            f"Se encontraron {len(datos)} llantas reencauchadas esta semana."
        )

    def _reporte_1mes(self) -> None:
        datos = InventarioKpiService.reporte_antiguedad(30)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte 1 mes",
            f"{len(datos)} llantas con ≥30 días en planta."
        )

    def _reporte_3meses(self) -> None:
        datos = InventarioKpiService.reporte_antiguedad(90)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte 3 meses",
            f"{len(datos)} llantas con ≥90 días en planta."
        )

    def _reporte_6meses(self) -> None:
        datos = InventarioKpiService.reporte_antiguedad(180)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte 6 meses",
            f"{len(datos)} llantas con ≥180 días en planta."
        )

    def _reporte_12meses(self) -> None:
        datos = InventarioKpiService.reporte_antiguedad(365)
        self._poblar_tabla_term(datos)
        self.tabs.setCurrentIndex(1)
        QMessageBox.information(
            self, "Reporte 12 meses",
            f"{len(datos)} llantas con ≥365 días en planta."
        )

    # ── MP Reports ──────────────────────────────────────────────────

    def _reporte_mp_stock(self) -> None:
        """Show MP stock report in the MP table."""
        self._cargar_mp()
        self.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self, "Stock MP",
            f"Reporte de stock general de materia prima ({len(self._mp_cache)} productos)."
        )

    def _reporte_mp_reorden(self) -> None:
        """Filter MP table to show only products below minimum stock."""
        bajos = [
            p for p in self._mp_cache
            if (p.stock or 0) < (p.stock_minimo or 0)
        ]
        self._poblar_tabla_mp(bajos)
        self.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self, "Punto de Reorden",
            f"{len(bajos)} productos de MP están por debajo del mínimo en planta."
        )

    # ── Consumible Reports ─────────────────────────────────────────

    def _reporte_cons_stock(self) -> None:
        """Show consumibles stock report in the consumibles table."""
        self._cargar_consumibles()
        self.tabs.setCurrentIndex(2)
        QMessageBox.information(
            self, "Stock Consumibles",
            f"Reporte de stock general de consumibles ({len(self._cons_cache)} productos)."
        )

    def _reporte_cons_reorden(self) -> None:
        """Filter consumibles table to show only products below minimum stock."""
        bajos = [
            p for p in self._cons_cache
            if (p.stock or 0) < (p.stock_minimo or 0)
        ]
        self._poblar_tabla_consumibles(bajos)
        self.tabs.setCurrentIndex(2)
        QMessageBox.information(
            self, "Punto de Reorden Consumibles",
            f"{len(bajos)} consumibles están por debajo del mínimo en planta."
        )

    def _exportar_excel(self) -> None:
        QMessageBox.information(
            self, "Exportar",
            "Exportación a Excel disponible en próxima versión."
        )