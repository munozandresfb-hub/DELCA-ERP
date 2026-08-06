"""Métodos de la pestaña Clientes del ReportesView."""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.modules.reportes.services.reporte_service import ReporteService
from src.modules.reportes.views.reportes_view._report_tab import _ReportTab


class _ClientesReportView:
    """Sección clientes: por ciudad, activos/inactivos y mayor saldo."""

    # ── Setup ─────────────────────────────────────────────────────

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
        from typing import cast

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
        from datetime import datetime as dt
        from typing import cast

        desde = self._ms_fecha_desde.date().toPython()
        hasta = self._ms_fecha_hasta.date().toPython()
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

    def _exportar_activos_inactivos(self) -> None:
        self._exportar_tabla(self._tab_act_inact, "clientes_activos_inactivos")

    def _exportar_mayor_saldo(self) -> None:
        self._exportar_tabla(self._tab_mayor_saldo, "clientes_mayor_saldo")