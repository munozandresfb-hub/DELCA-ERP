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
    """Sección clientes: activos/inactivos, mayor saldo e inactividad."""

    # ── Setup ─────────────────────────────────────────────────────

    def _setup_clientes_tab(self) -> None:
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
        btn_visualizar_ai = QPushButton("👁️ Visualizar")
        btn_visualizar_ai.clicked.connect(self._refresh_activos_inactivos)
        act_inact_toolbar.addWidget(btn_visualizar_ai)
        btn_export_ai = QPushButton("📊 Exportar Excel")
        btn_export_ai.clicked.connect(self._exportar_activos_inactivos)
        act_inact_toolbar.addWidget(btn_export_ai)
        tab2_layout.addLayout(act_inact_toolbar)

        self._tab_act_inact = _ReportTab("Act/Inact")
        self._tab_act_inact.set_columns([
            "Cliente", "Contacto", "NIT/Cédula", "Llantas en Planta",
            "Estado", "Última Vez",
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
        btn_visualizar_ms = QPushButton("👁️ Visualizar")
        btn_visualizar_ms.clicked.connect(self._refresh_mayor_saldo)
        ms_toolbar.addWidget(btn_visualizar_ms)
        btn_export_ms = QPushButton("📊 Exportar Excel")
        btn_export_ms.clicked.connect(self._exportar_mayor_saldo)
        ms_toolbar.addWidget(btn_export_ms)
        tab3_layout.addLayout(ms_toolbar)

        self._tab_mayor_saldo = _ReportTab("Mayor Saldo")
        self._tab_mayor_saldo.set_columns([
            "Cliente", "Contacto", "NIT/Cédula",
            "Saldo Pendiente", "Fecha Saldo", "Correo Electrónico",
        ])
        tab3_layout.addWidget(self._tab_mayor_saldo)

        # ── Inactividad (reactivación comercial) ────────────────────
        tab4_container = QWidget()
        tab4_layout = QVBoxLayout(tab4_container)
        tab4_layout.setContentsMargins(0, 0, 0, 0)

        inact_toolbar = QHBoxLayout()
        inact_toolbar.addWidget(QLabel("Días mínimos:"))
        self._inact_dias = QComboBox()
        self._inact_dias.addItems(["300", "365", "545", "730", "1095"])
        self._inact_dias.currentTextChanged.connect(self._refresh_inactividad)
        inact_toolbar.addWidget(self._inact_dias)
        inact_toolbar.addWidget(QLabel("Corte:"))
        self._inact_corte = QDateEdit()
        self._inact_corte.setCalendarPopup(True)
        self._inact_corte.setDate(QDate.currentDate())
        self._inact_corte.dateChanged.connect(self._refresh_inactividad)
        inact_toolbar.addWidget(self._inact_corte)
        inact_toolbar.addWidget(QLabel("Rango:"))
        self._inact_rango = QComboBox()
        self._inact_rango.addItems(
            ["Todos", "300-365", "366-730", "731-1095", "1096+"]
        )
        self._inact_rango.currentTextChanged.connect(self._refresh_inactividad)
        inact_toolbar.addWidget(self._inact_rango)
        inact_toolbar.addStretch()
        btn_visualizar_inact = QPushButton("👁️ Visualizar")
        btn_visualizar_inact.clicked.connect(self._refresh_inactividad)
        inact_toolbar.addWidget(btn_visualizar_inact)
        btn_export_inact = QPushButton("📊 Exportar Excel")
        btn_export_inact.clicked.connect(self._exportar_inactividad)
        inact_toolbar.addWidget(btn_export_inact)
        btn_mensual_inact = QPushButton("🗓️ Reporte Mensual")
        btn_mensual_inact.clicked.connect(self._exportar_inactividad_mensual)
        inact_toolbar.addWidget(btn_mensual_inact)
        tab4_layout.addLayout(inact_toolbar)

        self._tab_inactividad = _ReportTab("Inactividad")
        self._tab_inactividad.set_columns([
            "Cliente", "Contacto", "NIT/Cédula", "Ciudad", "Correo",
            "Llantas Aptas", "Segmento (Dimensión)", "Última Actividad",
            "Días sin Actividad", "Rango",
        ])
        tab4_layout.addWidget(self._tab_inactividad)

        # ── Tabs ─────────────────────────────────────────────────
        self._clientes_tabs = QTabWidget()
        self._clientes_tabs.addTab(tab2_container, "Activos/Inactivos")
        self._clientes_tabs.addTab(tab3_container, "Mayor Saldo")
        self._clientes_tabs.addTab(tab4_container, "Inactividad")

        self.tabs.addTab(self._clientes_tabs, "Clientes")

        # NOTA: sin refresco aquí — la pestaña carga de forma diferida
        # (solo la pestaña visible al abrir el módulo; ver ReportesView.setup_ui)

    def _refresh_clientes(self) -> None:
        self._refresh_activos_inactivos()
        self._refresh_mayor_saldo()
        self._refresh_inactividad()

    def _refresh_activos_inactivos(self) -> None:
        from datetime import datetime as dt
        from typing import cast

        try:
            filtro_map = {"Todos": None, "Activo": "ACTIVO", "Inactivo": "INACTIVO"}
            estado = filtro_map.get(self._act_inact_filter.currentText())
            desde = self._ai_fecha_desde.date().toPython()
            hasta = self._ai_fecha_hasta.date().toPython()
            data = ReporteService.clientes_activos_vs_inactivos(
                filtro=estado,
                fecha_desde=dt.combine(cast(dt, desde), dt.min.time()),
                fecha_hasta=dt.combine(cast(dt, hasta), dt.max.time()),
            )
        except Exception as e:
            # Nunca dejar la UI bloqueada ni abortar por un error del service
            self._tab_act_inact.clear_rows()
            self._tab_act_inact.add_row([f"(Error al generar el reporte: {e})"] * 6)
            return
        self._tab_act_inact.clear_rows()
        total_llantas = 0
        for r in data:
            self._tab_act_inact.add_row([
                r["nombre"],
                r["contacto"],
                r["nit"],
                str(r["llantas_planta"]),
                "Activo" if r["activo"] else "Inactivo",
                r["ultima_vez"],
            ])
            total_llantas += r["llantas_planta"]
        if data:
            self._tab_act_inact.clear_summaries()
            self._tab_act_inact.add_summary(
                f"Clientes en el reporte: {len(data)}  |  "
                f"Llantas en planta: {total_llantas}",
            )
        else:
            self._tab_act_inact.add_row(["(sin datos)"] * 6)

    def _refresh_mayor_saldo(self) -> None:
        from datetime import datetime as dt
        from typing import cast

        try:
            desde = self._ms_fecha_desde.date().toPython()
            hasta = self._ms_fecha_hasta.date().toPython()
            data = ReporteService.clientes_con_mayor_saldo_detalle(
                limite=20,
                fecha_desde=dt.combine(cast(dt, desde), dt.min.time()),
                fecha_hasta=dt.combine(cast(dt, hasta), dt.max.time()),
            )
        except Exception as e:
            self._tab_mayor_saldo.clear_rows()
            self._tab_mayor_saldo.add_row([f"(Error al generar el reporte: {e})"] * 6)
            return
        self._tab_mayor_saldo.clear_rows()
        total_saldo = 0
        for r in data:
            self._tab_mayor_saldo.add_row([
                r["nombre"],
                r["contacto"],
                r["nit"],
                f"${r['saldo']:,.2f}",
                r["fecha_saldo"],
                r["email"],
            ])
            total_saldo += r["saldo"]
        if data:
            self._tab_mayor_saldo.clear_summaries()
            self._tab_mayor_saldo.add_summary(
                f"Total saldo pendiente: ${total_saldo:,.2f}",
                color="#e74c3c",
            )
        else:
            self._tab_mayor_saldo.add_row(["(No hay clientes con saldo pendiente)"] * 6)

    def _exportar_activos_inactivos(self) -> None:
        self._exportar_tabla(self._tab_act_inact, "clientes_activos_inactivos")

    def _exportar_mayor_saldo(self) -> None:
        self._exportar_tabla(self._tab_mayor_saldo, "clientes_mayor_saldo")

    def _refresh_inactividad(self) -> None:
        from datetime import datetime as dt
        from typing import cast

        try:
            corte = self._inact_corte.date().toPython()
            data = ReporteService.clientes_inactivos(
                dias_minimo=int(self._inact_dias.currentText()),
                fecha_corte=dt.combine(cast(dt, corte), dt.max.time()),
            )
        except Exception as e:
            self._tab_inactividad.clear_rows()
            self._tab_inactividad.add_row([f"(Error al generar el reporte: {e})"] * 10)
            return

        rango_filtro = self._inact_rango.currentText()
        self._tab_inactividad.clear_rows()
        total_inactivos = 0
        total_primer_venta = 0
        total_aptas = 0
        for r in data:
            if rango_filtro != "Todos" and not r["rango_inactividad"].startswith(rango_filtro):
                continue
            if r["es_primer_venta"]:
                total_primer_venta += 1
            else:
                total_inactivos += 1
                total_aptas += r["llantas_aptas"]
            self._tab_inactividad.add_row([
                r["nombre"],
                r["contacto"],
                r["nit"],
                r["ciudad"],
                r["email"],
                str(r["llantas_aptas"]),
                r["segmento_dimension"],
                r["ultima_vez"],
                str(r["dias_sin_actividad"]),
                r["rango_inactividad"],
            ])
        if total_inactivos or total_primer_venta:
            self._tab_inactividad.clear_summaries()
            self._tab_inactividad.add_summary(
                f"Inactivos: {total_inactivos}  |  1er venta: {total_primer_venta}  |  "
                f"Llantas aptas: {total_aptas}  |  Corte: {corte}",
                color="#e74c3c",
            )
        else:
            self._tab_inactividad.add_row(["(Sin clientes inactivos)"] * 10)

    def _exportar_inactividad(self) -> None:
        self._exportar_tabla(self._tab_inactividad, "clientes_inactivos")

    def _exportar_inactividad_mensual(self) -> None:
        # Reporte mensual: nombre con el mes actual para trazabilidad
        mes = QDate.currentDate().toString("yyyy-MM")
        self._exportar_tabla(self._tab_inactividad, f"clientes_inactivos_{mes}")