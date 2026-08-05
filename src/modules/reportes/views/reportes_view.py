import os
from typing import cast

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.reportes.services.reporte_service import ReporteService


class _ReportTab(QWidget):
    """Base tab with a table and optional summary labels."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title
        self._widgets: list[QLabel] = []
        self.table: QTableWidget | None = None
        self.setup_base_ui()

    def setup_base_ui(self) -> None:
        layout = QVBoxLayout()

        self._summary_layout = QHBoxLayout()
        layout.addLayout(self._summary_layout)

        self.table = QTableWidget()
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

    def clear_summaries(self) -> None:
        """Remove all summary labels to prevent accumulation on refresh."""
        while self._widgets:
            widget = self._widgets.pop()
            self._summary_layout.removeWidget(widget)
            widget.deleteLater()

    def add_summary(self, text: str, color: str = "#2c3e50") -> None:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {color}; "
            f"padding: 6px 14px; background: #f8f9fa; "
            f"border-radius: 6px;"
        )
        self._summary_layout.addWidget(lbl)
        self._widgets.append(lbl)

    def set_columns(self, cols: list[str]) -> None:
        if self.table:
            self.table.setColumnCount(len(cols))
            self.table.setHorizontalHeaderLabels(cols)

    def clear_rows(self) -> None:
        if self.table:
            self.table.setRowCount(0)

    def add_row(self, values: list[str]) -> None:
        if not self.table:
            return
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, val in enumerate(values):
            self.table.setItem(row, col, QTableWidgetItem(str(val)))


class ReportesView(QWidget):
    """Multi-tab report view."""

    def __init__(self) -> None:
        super().__init__()
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # Header
        header = QLabel("Reportes")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px 0;"
        )
        layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        refresh_btn = QPushButton("🔄 Actualizar Todos")
        refresh_btn.clicked.connect(self._refresh_all)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)

        # Tabs
        self.tabs = QTabWidget()

        self._setup_clientes_tab()
        self._setup_llantas_tab()
        self._setup_indicadores_tab()
        self._setup_finanzas_tab()
        self._setup_inventario_tab()
        self._setup_resumen_tab()

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def _setup_clientes_tab(self) -> None:
        # ── Por Ciudad ───────────────────────────────────────────
        tab = _ReportTab("Clientes")
        tab.set_columns([
            "Cliente", "Contacto", "NIT/Cédula", "Ciudad",
            "Llantas en Planta", "Estado",
        ])

        # ── Activos/Inactivos ─────────────────────────────────────
        tab2_container = QWidget()
        tab2_layout = QVBoxLayout(tab2_container)
        tab2_layout.setContentsMargins(0, 0, 0, 0)

        # Filter toolbar
        act_inact_toolbar = QHBoxLayout()
        act_inact_toolbar.addWidget(QLabel("Filtrar:"))
        self._act_inact_filter = QComboBox()
        self._act_inact_filter.addItems(["Todos", "Activo", "Inactivo"])
        self._act_inact_filter.currentTextChanged.connect(
            self._refresh_activos_inactivos
        )
        act_inact_toolbar.addWidget(self._act_inact_filter)
        act_inact_toolbar.addWidget(QLabel("Desde:"))
        self._ai_fecha_desde = QDateEdit()
        self._ai_fecha_desde.setCalendarPopup(True)
        self._ai_fecha_desde.setDate(QDate.currentDate().addMonths(-12))
        self._ai_fecha_desde.dateChanged.connect(self._refresh_activos_inactivos)
        act_inact_toolbar.addWidget(self._ai_fecha_desde)
        act_inact_toolbar.addWidget(QLabel("Hasta:"))
        self._ai_fecha_hasta = QDateEdit()
        self._ai_fecha_hasta.setCalendarPopup(True)
        self._ai_fecha_hasta.setDate(QDate.currentDate())
        self._ai_fecha_hasta.dateChanged.connect(self._refresh_activos_inactivos)
        act_inact_toolbar.addWidget(self._ai_fecha_hasta)
        act_inact_toolbar.addStretch()
        btn_export_ai = QPushButton("📊 Exportar Excel")
        btn_export_ai.clicked.connect(self._exportar_activos_inactivos)
        act_inact_toolbar.addWidget(btn_export_ai)
        tab2_layout.addLayout(act_inact_toolbar)

        self._tab_act_inact = _ReportTab("Act/Inact")
        self._tab_act_inact.set_columns([
            "Cliente", "Contacto", "NIT/Cédula", "N° Cliente", "Estado", "Última Vez",
        ])
        tab2_layout.addWidget(self._tab_act_inact)

        # ── Mayor Saldo ──────────────────────────────────────────
        tab3_container = QWidget()
        tab3_layout = QVBoxLayout(tab3_container)
        tab3_layout.setContentsMargins(0, 0, 0, 0)

        # Filter toolbar
        ms_toolbar = QHBoxLayout()
        ms_toolbar.addWidget(QLabel("Desde:"))
        self._ms_fecha_desde = QDateEdit()
        self._ms_fecha_desde.setCalendarPopup(True)
        self._ms_fecha_desde.setDate(QDate.currentDate().addMonths(-3))
        self._ms_fecha_desde.dateChanged.connect(self._refresh_mayor_saldo)
        ms_toolbar.addWidget(self._ms_fecha_desde)
        ms_toolbar.addWidget(QLabel("Hasta:"))
        self._ms_fecha_hasta = QDateEdit()
        self._ms_fecha_hasta.setCalendarPopup(True)
        self._ms_fecha_hasta.setDate(QDate.currentDate())
        self._ms_fecha_hasta.dateChanged.connect(self._refresh_mayor_saldo)
        ms_toolbar.addWidget(self._ms_fecha_hasta)
        ms_toolbar.addStretch()
        btn_export_ms = QPushButton("📊 Exportar Excel")
        btn_export_ms.clicked.connect(self._exportar_mayor_saldo)
        ms_toolbar.addWidget(btn_export_ms)
        tab3_layout.addLayout(ms_toolbar)

        self._tab_mayor_saldo = _ReportTab("Mayor Saldo")
        self._tab_mayor_saldo.set_columns([
            "N° Cliente", "Cliente", "Contacto", "NIT",
            "Saldo Pendiente", "Fecha Saldo",
        ])
        tab3_layout.addWidget(self._tab_mayor_saldo)

        # ── Tabs ─────────────────────────────────────────────────
        self._clientes_tabs = QTabWidget()
        self._clientes_tabs.addTab(tab, "Por Ciudad")
        self._clientes_tabs.addTab(tab2_container, "Activos/Inactivos")
        self._clientes_tabs.addTab(tab3_container, "Mayor Saldo")

        self.tabs.addTab(self._clientes_tabs, "Clientes")

    def _setup_llantas_tab(self) -> None:
        """Single report view with filters + results table + KPI bar."""
        from PySide6.QtCore import QDate

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Filters toolbar ──────────────────────────────────────
        filters = QHBoxLayout()

        filters.addWidget(QLabel("Cliente:"))
        self._rep_cliente = QComboBox()
        self._rep_cliente.addItem("Todos", None)
        # populate clients from service
        try:
            from src.modules.reportes.services.reporte_service import ReporteService
            from src.database.engine import get_session
            from src.modules.clientes.models.cliente_model import Cliente
            with get_session() as session:
                clientes = session.query(Cliente.id, Cliente.nombre).order_by(Cliente.nombre).all()
                for cid, cname in clientes:
                    self._rep_cliente.addItem(cname, cid)
        except Exception:
            pass
        filters.addWidget(self._rep_cliente)

        filters.addWidget(QLabel("Estado:"))
        self._rep_estado = QComboBox()
        self._rep_estado.addItems(["Todos", "PENDIENTE", "APTA", "RECHAZADA", "REENCAUCHADA", "REPARADA"])
        filters.addWidget(self._rep_estado)

        filters.addWidget(QLabel("Ubicación:"))
        self._rep_ubicacion = QComboBox()
        self._rep_ubicacion.addItems(["Todas", "PRODUCCION", "PLANTA", "CLIENTE"])
        filters.addWidget(self._rep_ubicacion)

        layout.addLayout(filters)

        # ── Second row: dates + search + checkboxes ──────────────
        filters2 = QHBoxLayout()

        filters2.addWidget(QLabel("Desde:"))
        self._rep_desde = QDateEdit()
        self._rep_desde.setCalendarPopup(True)
        self._rep_desde.setDate(QDate.currentDate().addMonths(-3))
        filters2.addWidget(self._rep_desde)

        filters2.addWidget(QLabel("Hasta:"))
        self._rep_hasta = QDateEdit()
        self._rep_hasta.setCalendarPopup(True)
        self._rep_hasta.setDate(QDate.currentDate())
        filters2.addWidget(self._rep_hasta)

        self._rep_solo_planta = QCheckBox("Solo en planta")
        filters2.addWidget(self._rep_solo_planta)

        filters2.addStretch()
        layout.addLayout(filters2)

        # ── Third row: search + buttons ──────────────────────────
        filters3 = QHBoxLayout()

        self._rep_busqueda = QLineEdit()
        self._rep_busqueda.setPlaceholderText("🔍 Buscar tiquete, marca o dimensión...")
        filters3.addWidget(self._rep_busqueda)

        self._rep_btn_generar = QPushButton("🔍 Generar Reporte")
        self._rep_btn_generar.clicked.connect(self._refresh_reporte_llantas)
        filters3.addWidget(self._rep_btn_generar)

        self._rep_btn_exportar = QPushButton("📊 Exportar Excel")
        self._rep_btn_exportar.clicked.connect(self._exportar_reporte_llantas)
        filters3.addWidget(self._rep_btn_exportar)

        layout.addLayout(filters3)

        # ── KPI bar ──────────────────────────────────────────────
        self._rep_kpis = QLabel("Completa los filtros y presiona 'Generar Reporte'")
        self._rep_kpis.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #2c3e50; "
            "padding: 8px 14px; background: #f8f9fa; border-radius: 6px;"
        )
        layout.addWidget(self._rep_kpis)

        # ── Results table ────────────────────────────────────────
        self._tab_reporte_llantas = _ReportTab("Reporte Llantas")
        self._tab_reporte_llantas.set_columns([
            "Tiquete", "Cliente", "NIT", "Marca", "Dimensión", "Estado",
            "Ubicación", "Ingreso", "Días", "Costo", "Precio",
            "Utilidad", "Margen",
        ])
        layout.addWidget(self._tab_reporte_llantas)

        self.tabs.addTab(container, "📋 Llantas")

    def _refresh_reporte_llantas(self) -> None:
        """Generate report from current filter values."""
        from datetime import datetime as dt

        cliente_id = self._rep_cliente.currentData()
        estado_raw = self._rep_estado.currentText()
        estado = estado_raw if estado_raw != "Todos" else None
        ubic_raw = self._rep_ubicacion.currentText()
        ubicacion = ubic_raw if ubic_raw != "Todas" else None
        solo_planta = self._rep_solo_planta.isChecked()
        busqueda = self._rep_busqueda.text().strip() or None

        desde = self._rep_desde.date().toPython()
        hasta = self._rep_hasta.date().toPython()
        fecha_desde = dt.combine(cast(dt, desde), dt.min.time()) if desde else None
        fecha_hasta = dt.combine(cast(dt, hasta), dt.max.time()) if hasta else None

        data = ReporteService.reporte_llantas(
            cliente_id=cliente_id,
            estado=estado,
            ubicacion=ubicacion,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            busqueda=busqueda,
            solo_planta=solo_planta,
        )
        rows = data["rows"]
        kpis = data["kpis"]

        self._tab_reporte_llantas.clear_rows()
        total_valor = 0.0
        for r in rows:
            margen_str = f"{r['margen_pct']:.1f}%" if r['margen_pct'] is not None else "—"
            self._tab_reporte_llantas.add_row([
                r["tiquete"],
                r["cliente"],
                r["nit"],
                r["marca"],
                r["dimension"],
                r["estado"],
                r["ubicacion"],
                r["fecha_ingreso"],
                str(r["dias_planta"]),
                f"${r['costo']:,.2f}" if r['costo'] else "$0",
                f"${r['precio']:,.2f}" if r['precio'] else "—",
                f"${r['utilidad']:,.2f}",
                margen_str,
            ])
            total_valor += r["costo"]

            # Highlight negative margins
            if r["margen_pct"] is not None and r["margen_pct"] < 0:
                tbl = self._tab_reporte_llantas.table
                if tbl:
                    last = tbl.rowCount() - 1
                    for c in range(tbl.columnCount()):
                        item = tbl.item(last, c)
                        if item:
                            item.setForeground(QBrush(QColor("#e74c3c")))

        if rows:
            self._tab_reporte_llantas.clear_summaries()
            self._tab_reporte_llantas.add_summary(
                f"Total: {kpis['total']} llantas  |  "
                f"En planta: {kpis['en_planta']}  |  "
                f"Valor inventario: ${kpis['valor_inventario']:,.2f}  |  "
                f">30 días: {kpis['mas_30d']}  |  "
                f"Util. potencial: ${kpis['utilidad_potencial']:,.2f}",
                color="#2c3e50",
            )
        else:
            self._tab_reporte_llantas.add_row(["(sin resultados)"] * 13)

        # Update KPI bar
        self._rep_kpis.setText(
            f"📌 {kpis['total']} llantas · "
            f"{kpis['en_planta']} en planta · "
            f"${kpis['valor_inventario']:,.0f} valor · "
            f"{kpis['mas_30d']} >30d · "
            f"Con precio: {kpis['con_precio']} / Sin: {kpis['sin_precio']}"
        )

    def _exportar_reporte_llantas(self) -> None:
        self._exportar_tabla(
            self._tab_reporte_llantas, "reporte_llantas"
        )

    def _setup_finanzas_tab(self) -> None:
        # por Mes (con selector de mes)
        tab_container = QWidget()
        tab_layout = QVBoxLayout(tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        mes_toolbar = QHBoxLayout()
        mes_toolbar.addWidget(QLabel("Mes:"))
        self._fin_mes_selector = QDateEdit()
        self._fin_mes_selector.setCalendarPopup(True)
        self._fin_mes_selector.setDisplayFormat("MMMM yyyy")
        self._fin_mes_selector.setDate(QDate.currentDate())
        self._fin_mes_selector.dateChanged.connect(self._refresh_por_mes)
        mes_toolbar.addWidget(self._fin_mes_selector)
        mes_toolbar.addStretch()
        btn_export_mes = QPushButton("📊 Exportar Excel")
        btn_export_mes.clicked.connect(self._exportar_por_mes)
        mes_toolbar.addWidget(btn_export_mes)
        tab_layout.addLayout(mes_toolbar)
        self._tab_por_mes = _ReportTab("por Mes")
        self._tab_por_mes.set_columns([
            "N° Factura", "N° Cliente", "Cliente", "NIT",
            "Valor", "Saldo", "Estado", "Fecha",
        ])
        tab_layout.addWidget(self._tab_por_mes)

        # por Estado
        tab3_container = QWidget()
        tab3_layout = QVBoxLayout(tab3_container)
        tab3_layout.setContentsMargins(0, 0, 0, 0)
        est_toolbar = QHBoxLayout()
        est_toolbar.addWidget(QLabel("Filtrar Estado:"))
        self._fin_estado_filter = QComboBox()
        self._fin_estado_filter.addItems([
            "Todos", "PENDIENTE", "PAGADA", "ANULADA",
        ])
        self._fin_estado_filter.currentTextChanged.connect(
            self._refresh_por_estado
        )
        est_toolbar.addWidget(self._fin_estado_filter)
        est_toolbar.addStretch()
        btn_export_est = QPushButton("📊 Exportar Excel")
        btn_export_est.clicked.connect(self._exportar_por_estado)
        est_toolbar.addWidget(btn_export_est)
        tab3_layout.addLayout(est_toolbar)
        self._tab_por_estado = _ReportTab("por Estado")
        self._tab_por_estado.set_columns([
            "N° Factura", "N° Cliente", "Cliente", "NIT",
            "Valor", "Saldo", "Fecha", "Estado",
        ])
        tab3_layout.addWidget(self._tab_por_estado)

        # Detalle Llantas (con búsqueda)
        tab4_container = QWidget()
        tab4_layout = QVBoxLayout(tab4_container)
        tab4_layout.setContentsMargins(0, 0, 0, 0)
        llantas_toolbar = QHBoxLayout()
        llantas_toolbar.addWidget(QLabel("Buscar:"))
        self._fin_llantas_busqueda = QLineEdit()
        self._fin_llantas_busqueda.setPlaceholderText(
            "Tiquete, marca o dimensión..."
        )
        self._fin_llantas_busqueda.textChanged.connect(
            self._refresh_detalle_llantas
        )
        llantas_toolbar.addWidget(self._fin_llantas_busqueda)
        llantas_toolbar.addStretch()
        btn_export_ll = QPushButton("📊 Exportar Excel")
        btn_export_ll.clicked.connect(self._exportar_detalle_llantas)
        llantas_toolbar.addWidget(btn_export_ll)
        tab4_layout.addLayout(llantas_toolbar)
        self._tab_detalle_llantas = _ReportTab("Detalle Llantas")
        self._tab_detalle_llantas.set_columns([
            "Tiquete", "Marca", "Dimensión", "Estado",
            "Ubicación", "Cliente", "NIT",
            "Costo", "Precio Venta",
        ])
        tab4_layout.addWidget(self._tab_detalle_llantas)

        self._finanzas_tabs = QTabWidget()
        self._finanzas_tabs.addTab(tab_container, "por Mes")
        self._finanzas_tabs.addTab(tab3_container, "por Estado")
        self._finanzas_tabs.addTab(tab4_container, "Detalle Llantas")
        self.tabs.addTab(self._finanzas_tabs, "Finanzas")

    def _setup_inventario_tab(self) -> None:
        tab = _ReportTab("por Categoría")
        tab.set_columns(
            ["Categoría", "Producto", "Código", "Stock", "Valor"]
        )

        tab2 = _ReportTab("Movimientos por Tipo")
        tab2.set_columns(["Consecutivo", "Tipo", "Cant. Mov.", "Unidades"])

        tab3 = _ReportTab("Stock Bajo")
        tab3.set_columns(["Producto", "SKU", "Stock"])

        self._inventario_tabs = QTabWidget()
        self._inventario_tabs.addTab(tab, "por Categoría")
        self._inventario_tabs.addTab(tab2, "Movimientos")
        self._inventario_tabs.addTab(tab3, "Stock Bajo")
        self.tabs.addTab(self._inventario_tabs, "Inventario")

    def _setup_resumen_tab(self) -> None:
        tab = _ReportTab("Resumen General")
        tab.set_columns(["Métrica", "Valor"])
        self.tabs.addTab(tab, "Resumen")

    def _refresh_all(self) -> None:
        self._refresh_clientes()
        self._refresh_reporte_llantas()
        self._refresh_indicadores()
        self._refresh_finanzas()
        self._refresh_inventario()
        self._refresh_resumen()

    def _refresh_clientes(self) -> None:
        self._refresh_por_ciudad()
        self._refresh_activos_inactivos()
        self._refresh_mayor_saldo()

    def _refresh_por_ciudad(self) -> None:
        tab = self._clientes_tabs.widget(0)
        if not isinstance(tab, _ReportTab):
            return
        tab.clear_rows()
        data = ReporteService.clientes_por_ciudad()
        total_llantas = 0
        for r in data:
            tab.add_row([
                r["nombre"],
                r["contacto"],
                r["nit"],
                r["ciudad"],
                str(r["llantas_planta"]),
                "Activo" if r["activo"] else "Inactivo",
            ])
            total_llantas += r["llantas_planta"]
        if data:
            tab.clear_summaries()
            tab.add_summary(
                f"Total clientes: {len(data)}  |  "
                f"Llantas en planta: {total_llantas}",
            )
        else:
            tab.add_row(["(sin datos)"] * 6)

    def _refresh_activos_inactivos(self) -> None:
        from datetime import datetime as dt
        filtro_map = {"Todos": None, "Activo": "ACTIVO", "Inactivo": "INACTIVO"}
        estado = filtro_map.get(self._act_inact_filter.currentText())
        desde = self._ai_fecha_desde.date().toPython()
        hasta = self._ai_fecha_hasta.date().toPython()
        data = ReporteService.clientes_activos_vs_inactivos(
            filtro=estado,
            fecha_desde=dt.combine(cast(dt, desde), dt.min.time()),
            fecha_hasta=dt.combine(cast(dt, hasta), dt.max.time()),
        )
        self._tab_act_inact.clear_rows()
        for r in data:
            self._tab_act_inact.add_row([
                r["nombre"],
                r["contacto"],
                r["nit"],
                str(r["id"]),
                "Activo" if r["activo"] else "Inactivo",
                r["ultima_vez"],
            ])
        if not data:
            self._tab_act_inact.add_row(["(sin datos)"] * 6)

    def _refresh_mayor_saldo(self) -> None:
        desde = self._ms_fecha_desde.date().toPython()
        hasta = self._ms_fecha_hasta.date().toPython()
        from datetime import datetime as dt
        data = ReporteService.clientes_con_mayor_saldo_detalle(
            limite=20,
            fecha_desde=dt.combine(cast(dt, desde), dt.min.time()),
            fecha_hasta=dt.combine(cast(dt, hasta), dt.max.time()),
        )
        self._tab_mayor_saldo.clear_rows()
        total_saldo = 0
        for r in data:
            self._tab_mayor_saldo.add_row([
                str(r["id"]),
                r["nombre"],
                r["contacto"],
                r["nit"],
                f"${r['saldo']:,.2f}",
                r["fecha_saldo"],
            ])
            total_saldo += r["saldo"]
        if data:
            self._tab_mayor_saldo.clear_summaries()
            self._tab_mayor_saldo.add_summary(
                f"Total saldo pendiente: ${total_saldo:,.2f}",
                color="#e74c3c",
            )
        else:
            self._tab_mayor_saldo.add_row(["(sin datos)"] * 6)

    # ── Export handlers ──────────────────────────────────────────

    def _exportar_tabla(self, tab: _ReportTab, nombre_base: str) -> None:
        if not tab.table:
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, f"Guardar {nombre_base}",
            f"{nombre_base}.xlsx", "Excel (*.xlsx)",
        )
        if not ruta:
            return
        headers = []
        for ci in range(tab.table.columnCount()):
            item = tab.table.horizontalHeaderItem(ci)
            headers.append(item.text() if item else "")
        rows = []
        for ri in range(tab.table.rowCount()):
            row = []
            for ci in range(tab.table.columnCount()):
                item = tab.table.item(ri, ci)
                row.append(item.text() if item else "")
            rows.append(row)
        ok = ReporteService.exportar_excel(ruta, headers, rows)
        if ok:
            QMessageBox.information(
                self, "Exportar Excel",
                f"✓ Exportado:\n{os.path.basename(ruta)}",
            )
        else:
            QMessageBox.warning(
                self, "Exportar Excel",
                "No se pudo exportar. ¿openpyxl está instalado?",
            )

    def _exportar_activos_inactivos(self) -> None:
        self._exportar_tabla(self._tab_act_inact, "clientes_activos_inactivos")

    def _exportar_mayor_saldo(self) -> None:
        self._exportar_tabla(self._tab_mayor_saldo, "clientes_mayor_saldo")

    def _exportar_por_mes(self) -> None:
        self._exportar_tabla(self._tab_por_mes, "facturas_por_mes")

    def _exportar_por_estado(self) -> None:
        self._exportar_tabla(self._tab_por_estado, "facturas_por_estado")

    def _exportar_detalle_llantas(self) -> None:
        self._exportar_tabla(self._tab_detalle_llantas, "detalle_llantas")

    def _setup_indicadores_tab(self) -> None:
        """Independent improved Indicators dashboard."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── KPI cards row ───────────────────────────────────────
        kpi_row = QHBoxLayout()
        self._ind_kpis: dict[str, QLabel] = {}
        kpi_configs = [
            ("Valor Inventario", "valor_inventario_planta", "$0", "#3498db"),
            ("Llantas Planta", "total_llantas_planta", "0", "#27ae60"),
            ("Util. Bruta Prom.", "promedio_utilidad_bruta", "$0", "#f39c12"),
            ("Con / Sin Precio", "con_sin_precio", "0 / 0", "#95a5a6"),
            ("Util. Potencial", "total_utilidad_potencial", "$0", "#2c3e50"),
        ]
        for label, key, default, color in kpi_configs:
            frame = QFrame()
            frame.setStyleSheet(
                f"QFrame {{ background: white; border: 1px solid {color}; "
                f"border-radius: 8px; padding: 8px; }}"
            )
            f_layout = QVBoxLayout(frame)
            val = QLabel(default)
            val.setStyleSheet(
                f"font-size: 18px; font-weight: bold; color: {color};"
            )
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            f_layout.addWidget(val)
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; color: #7f8c8d;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            f_layout.addWidget(lbl)
            self._ind_kpis[key] = val
            kpi_row.addWidget(frame)

        layout.addLayout(kpi_row)

        # ── Estado breakdown + Top Clientes ─────────────────────
        mid_row = QHBoxLayout()

        # Left: Estado table
        est_container = QWidget()
        est_layout = QVBoxLayout(est_container)
        est_layout.setContentsMargins(0, 0, 0, 0)
        est_layout.addWidget(QLabel("Llantas por Estado"))
        self._ind_estado_tab = _ReportTab("por Estado")
        self._ind_estado_tab.set_columns(["Estado", "Cantidad", "Valor"])
        est_layout.addWidget(self._ind_estado_tab)
        mid_row.addWidget(est_container)

        # Right: Top Clientes table
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(QLabel("Top Clientes por Volumen"))
        self._ind_top_clientes = _ReportTab("Top Clientes")
        self._ind_top_clientes.set_columns(["Cliente", "Cantidad Llantas"])
        top_layout.addWidget(self._ind_top_clientes)
        mid_row.addWidget(top_container)

        layout.addLayout(mid_row)

        # ── Detail table ────────────────────────────────────────
        layout.addWidget(QLabel("Detalle de Llantas en Planta"))
        self._ind_detalle = _ReportTab("Detalle")
        self._ind_detalle.set_columns([
            "Tiquete", "Cliente", "Estado", "Ubicación",
            "Costo $", "Precio $", "Utilidad $", "Margen %",
        ])
        layout.addWidget(self._ind_detalle)

        self.tabs.addTab(container, "📊 Indicadores")

    def _refresh_indicadores(self) -> None:
        """Load indicators data."""
        data = ReporteService.indicadores_llantas()
        res = data["resumen"]
        detalle = data["detalle"]
        por_estado = data.get("por_estado", [])
        top_clientes = data.get("top_clientes", [])

        # ── KPI cards ──
        self._ind_kpis["valor_inventario_planta"].setText(
            f"${res['valor_inventario_planta']:,.2f}"
        )
        self._ind_kpis["total_llantas_planta"].setText(
            str(res["total_llantas_planta"])
        )
        self._ind_kpis["promedio_utilidad_bruta"].setText(
            f"${res['promedio_utilidad_bruta']:,.2f}"
        )
        self._ind_kpis["con_sin_precio"].setText(
            f"{res['llantas_con_precio']} / {res['llantas_sin_precio']}"
        )
        self._ind_kpis["total_utilidad_potencial"].setText(
            f"${res['total_utilidad_potencial']:,.2f}"
        )

        # ── Estado table ──
        self._ind_estado_tab.clear_rows()
        for r in por_estado:
            self._ind_estado_tab.add_row([
                r["estado"],
                str(r["cantidad"]),
                f"${r['valor']:,.2f}",
            ])
        if not por_estado:
            self._ind_estado_tab.add_row(["(sin datos)"] * 3)

        # ── Top clientes table ──
        self._ind_top_clientes.clear_rows()
        for r in top_clientes:
            self._ind_top_clientes.add_row([
                r["cliente"],
                str(r["cantidad"]),
            ])
        if not top_clientes:
            self._ind_top_clientes.add_row(["(sin datos)"] * 2)

        # ── Detail table ──
        self._ind_detalle.clear_rows()
        self._ind_detalle.clear_summaries()
        for r in detalle:
            margen_str = f"{r['margen_pct']:.1f}%" if r['margen_pct'] is not None else "—"
            self._ind_detalle.add_row([
                r["tiquete"],
                r["cliente"],
                r["estado"],
                r["ubicacion"],
                f"${r['costo']:,.2f}" if r['costo'] else "—",
                f"${r['precio']:,.2f}" if r['precio'] else "—",
                f"${r['utilidad']:,.2f}",
                margen_str,
            ])
            # Highlight negative margins
            if r["margen_pct"] is not None and r["margen_pct"] < 0:
                tbl = self._ind_detalle.table
                if tbl:
                    last = tbl.rowCount() - 1
                    for c in range(tbl.columnCount()):
                        item = tbl.item(last, c)
                        if item:
                            item.setForeground(QBrush(QColor("#e74c3c")))

        if not detalle:
            self._ind_detalle.add_row(["(sin datos)"] * 8)
        else:
            total_costo = sum(r["costo"] or 0 for r in detalle)
            total_venta = sum(r["precio"] or 0 for r in detalle)
            utilidad = total_venta - total_costo
            self._ind_detalle.add_summary(
                f"Total Costo: ${total_costo:,.2f}  |  "
                f"Total Venta: ${total_venta:,.2f}  |  "
                f"Utilidad: ${utilidad:,.2f}",
                color="#2c3e50",
            )

    def _refresh_finanzas(self) -> None:
        self._refresh_por_mes()
        self._refresh_por_estado()
        self._refresh_detalle_llantas()

    def _refresh_por_mes(self) -> None:
        sel = self._fin_mes_selector.date()
        mes = sel.month()
        anio = sel.year()
        data = ReporteService.facturas_detalle_por_mes(anio, mes)
        self._tab_por_mes.clear_rows()
        total_valor = 0
        total_saldo = 0
        for r in data:
            self._tab_por_mes.add_row([
                str(r["id"]),
                str(r["cliente_id"]),
                r["cliente"],
                r["nit"],
                f"${r['valor']:,.2f}",
                f"${r['saldo']:,.2f}",
                str(r["estado"]),
                r["fecha"],
            ])
            total_valor += r["valor"]
            total_saldo += r["saldo"]
        if data:
            self._tab_por_mes.clear_summaries()
            pendientes = sum(1 for r in data if r["saldo"] > 0)
            self._tab_por_mes.add_summary(
                f"Facturas: {len(data)}  |  "
                f"Valor: ${total_valor:,.2f}  |  "
                f"Saldo pendiente: ${total_saldo:,.2f}  |  "
                f"Pendientes: {pendientes}",
                color="#2c3e50",
            )
        else:
            self._tab_por_mes.add_row(["(sin datos)"] * 8)

    def _refresh_por_estado(self) -> None:
        estado_raw = self._fin_estado_filter.currentText()
        estado = estado_raw if estado_raw != "Todos" else None
        data = ReporteService.facturas_por_estado_detalle(estado=estado)
        self._tab_por_estado.clear_rows()
        total_valor = 0
        total_saldo = 0
        for r in data:
            self._tab_por_estado.add_row([
                str(r["id"]),
                str(r["cliente_id"]),
                r["cliente"],
                r["nit"],
                f"${r['valor']:,.2f}",
                f"${r['saldo']:,.2f}",
                r["fecha"],
                str(r["estado"]),
            ])
            total_valor += r["valor"]
            total_saldo += r["saldo"]
        if data:
            self._tab_por_estado.clear_summaries()
            self._tab_por_estado.add_summary(
                f"Facturas: {len(data)}  |  "
                f"Valor: ${total_valor:,.2f}  |  "
                f"Saldo pendiente: ${total_saldo:,.2f}",
                color="#2c3e50",
            )
        else:
            self._tab_por_estado.add_row(["(sin datos)"] * 8)

    def _refresh_detalle_llantas(self) -> None:
        busqueda = self._fin_llantas_busqueda.text().strip().lower()
        data = ReporteService.detalle_financiero_llantas()
        self._tab_detalle_llantas.clear_rows()
        total_costo = 0.0
        total_venta = 0.0
        for r in data:
            if busqueda:
                tiquete = str(r.get("tiquete", "")).lower()
                mar = str(r.get("marca", "")).lower()
                med = str(r.get("dimension", "")).lower()
                if busqueda not in tiquete and busqueda not in mar and busqueda not in med:
                    continue
            self._tab_detalle_llantas.add_row([
                r["tiquete"],
                r["marca"],
                r["dimension"],
                r["estado"],
                r["ubicacion"],
                r["cliente"],
                r["nit"],
                f"${r['costo_produccion']:,.2f}" if r["costo_produccion"] else "$0",
                f"${r['precio_venta']:,.2f}" if r["precio_venta"] else "$0",
            ])
            total_costo += r["costo_produccion"] or 0
            total_venta += r["precio_venta"] or 0
        if data:
            self._tab_detalle_llantas.clear_summaries()
            utilidad = total_venta - total_costo
            self._tab_detalle_llantas.add_summary(
                f"Total Costo: ${total_costo:,.2f}  |  "
                f"Total Venta: ${total_venta:,.2f}  |  "
                f"Utilidad: ${utilidad:,.2f}",
                color="#2c3e50",
            )
            self._tab_detalle_llantas.add_summary(
                f"Mostrando: {self._tab_detalle_llantas.table.rowCount()} llantas",
                color="#27ae60",
            )
        else:
            self._tab_detalle_llantas.add_row(["(sin datos)"] * 9)

    def _refresh_inventario(self) -> None:
        # por Categoría (per-product detail)
        tab = self._inventario_tabs.widget(0)
        if isinstance(tab, _ReportTab):
            tab.clear_rows()
            data = ReporteService.inventario_por_categoria()
            total_valor = 0
            for r in data:
                tab.add_row(
                    [
                        r["categoria"],
                        r["producto"],
                        str(r["codigo"]),
                        str(r["stock"]),
                        f"${r['valor']:,.2f}",
                    ]
                )
                total_valor += r["valor"]
            if data:
                tab.clear_summaries()
                tab.add_summary(
                    f"Valor total: ${total_valor:,.2f}",
                    color="#27ae60",
                )
            else:
                tab.add_row(["(sin datos)"] * 5)

        # Movimientos
        tab2 = self._inventario_tabs.widget(1)
        if isinstance(tab2, _ReportTab):
            tab2.clear_rows()
            data = ReporteService.movimientos_por_tipo()
            for r in data:
                tab2.add_row(
                    [
                        str(r["consecutivo"]),
                        r["tipo"],
                        str(r["cantidad"]),
                        str(r["total_unidades"]),
                    ]
                )
            if not data:
                tab2.add_row(["(sin datos)"] * 4)

        # Stock bajo
        tab3 = self._inventario_tabs.widget(2)
        if isinstance(tab3, _ReportTab):
            tab3.clear_rows()
            data = ReporteService.productos_stock_bajo()
            for r in data:
                tab3.add_row(
                    [
                        r["nombre"],
                        r["sku"],
                        str(r["stock"]),
                    ]
                )
            if not data:
                tab3.add_row(["(sin datos)", "", ""])

    def _refresh_resumen(self) -> None:
        tab = self.tabs.widget(5)  # Resumen tab
        if isinstance(tab, _ReportTab):
            tab.clear_rows()
            data = ReporteService.obtener_resumen_completo()
            tab.add_row(["Clientes Activos", str(data["clientes_activos"])])
            tab.add_row(["Clientes Inactivos", str(data["clientes_inactivos"])])
            tab.add_row(["Total Clientes", str(data["total_clientes"])])
            tab.add_row(["Llantas en Planta", str(data["llantas_en_planta"])])
            tab.add_row(["Total Llantas (histórico)", str(data["total_llantas"])])
            tab.add_row(["Facturas Pendientes", str(data["facturas_pendientes"])])
            tab.add_row(["Total Facturas", str(data["total_facturas"])])
            tab.add_row(["Productos Stock Bajo", str(data["productos_stock_bajo"])])
            tab.add_row(["Total Productos", str(data["total_productos"])])
            tab.add_row(["Total Pagos", str(data["total_pagos"])])
            tab.add_row(
                [
                    "Total Mov. Inventario",
                    str(data["total_movimientos"]),
                ]
            )
            tab.add_row(
                [
                    "Facturación Anual",
                    f"${data['facturacion_anual']:,.2f}",
                ]
            )
            tab.add_row(
                [
                    "Valor Inventario",
                    f"${data['valor_inventario']:,.2f}",
                ]
            )
