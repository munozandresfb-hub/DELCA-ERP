"""Métodos de la pestaña Llantas (Reporte unificado) del ReportesView."""

from typing import cast

from PySide6.QtCore import QDate
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.modules.llantas.services.llanta_service import (
    ESTADOS_PROCESO,
    UBICACIONES_PLANTA,
)
from src.modules.reportes.services.reporte_service import ReporteService
from src.modules.reportes.views.reportes_view._report_tab import _ReportTab


class _LlantasReportView:
    """Sección Llantas: reporte unificado con filtros combinables."""

    def _setup_llantas_tab(self) -> None:
        """Single report view with filters + results table + KPI bar."""

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
        self._rep_estado.addItems(["Todos", *ESTADOS_PROCESO])
        filters.addWidget(self._rep_estado)

        filters.addWidget(QLabel("Ubicación:"))
        self._rep_ubicacion = QComboBox()
        self._rep_ubicacion.addItems(["Todas", *UBICACIONES_PLANTA])
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

        btn_visualizar_rep = QPushButton("👁️ Visualizar")
        btn_visualizar_rep.clicked.connect(self._refresh_reporte_llantas)
        filters3.addWidget(btn_visualizar_rep)

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
            # Limite de filas en la tabla (los KPIs se calculan en SQL
            # sobre el total, no sobre la pagina). Evita saturar la UI
            # con decenas de miles de filas.
            limite=2000,
            offset=0,
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