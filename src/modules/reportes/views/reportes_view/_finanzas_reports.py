"""Métodos de la pestaña Finanzas del ReportesView."""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.modules.reportes.services.reporte_service import ReporteService
from src.modules.reportes.views.reportes_view._report_tab import _ReportTab


class _FinanzasReportView:
    """Sección Finanzas: por mes, por estado y detalle de llantas."""

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
        btn_visualizar_mes = QPushButton("👁️ Visualizar")
        btn_visualizar_mes.clicked.connect(self._refresh_por_mes)
        mes_toolbar.addWidget(btn_visualizar_mes)
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
        btn_visualizar_est = QPushButton("👁️ Visualizar")
        btn_visualizar_est.clicked.connect(self._refresh_por_estado)
        est_toolbar.addWidget(btn_visualizar_est)
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
            "Tipo, tiquete, marca o dimensión..."
        )
        self._fin_llantas_busqueda.textChanged.connect(
            self._refresh_detalle_llantas
        )
        llantas_toolbar.addWidget(self._fin_llantas_busqueda)
        llantas_toolbar.addStretch()
        btn_visualizar_ll = QPushButton("👁️ Visualizar")
        btn_visualizar_ll.clicked.connect(self._refresh_detalle_llantas)
        llantas_toolbar.addWidget(btn_visualizar_ll)
        btn_export_ll = QPushButton("📊 Exportar Excel")
        btn_export_ll.clicked.connect(self._exportar_detalle_llantas)
        llantas_toolbar.addWidget(btn_export_ll)
        tab4_layout.addLayout(llantas_toolbar)
        self._tab_detalle_llantas = _ReportTab("Detalle Llantas")
        self._tab_detalle_llantas.set_columns([
            "Tipo", "Tiquete/Descripción", "Marca", "Dimensión", "Estado",
            "Ubicación", "Cliente", "NIT",
            "Costo", "Precio Venta",
        ])
        tab4_layout.addWidget(self._tab_detalle_llantas)

        self._finanzas_tabs = QTabWidget()
        self._finanzas_tabs.addTab(tab_container, "por Mes")
        self._finanzas_tabs.addTab(tab3_container, "por Estado")
        self._finanzas_tabs.addTab(tab4_container, "Detalle Llantas")
        self.tabs.addTab(self._finanzas_tabs, "Finanzas")

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
            self._tab_por_mes.add_row(["(No hay facturas en el periodo seleccionado)"] * 8)

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
            self._tab_por_estado.add_row(["(No hay facturas en el periodo seleccionado)"] * 8)

    def _refresh_detalle_llantas(self) -> None:
        busqueda = self._fin_llantas_busqueda.text().strip().lower()
        data = ReporteService.detalle_financiero_llantas()
        self._tab_detalle_llantas.clear_rows()
        total_costo = 0.0
        total_venta = 0.0
        cont_reencauchadas = 0
        cont_nuevas = 0
        for r in data:
            if busqueda:
                tipo = str(r.get("tipo", "")).lower()
                tiquete = str(r.get("tiquete", "")).lower()
                mar = str(r.get("marca", "")).lower()
                med = str(r.get("dimension", "")).lower()
                if (
                    busqueda not in tipo
                    and busqueda not in tiquete
                    and busqueda not in mar
                    and busqueda not in med
                ):
                    continue
            self._tab_detalle_llantas.add_row([
                r["tipo"],
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
            if r["tipo"] == "Llanta nueva":
                cont_nuevas += 1
            else:
                cont_reencauchadas += 1
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
                f"Mostrando: {self._tab_detalle_llantas.table.rowCount()} llantas "
                f"({cont_reencauchadas} reencauchadas · {cont_nuevas} nuevas)",
                color="#27ae60",
            )
        else:
            self._tab_detalle_llantas.add_row(["(sin datos)"] * 10)

    def _exportar_por_mes(self) -> None:
        self._exportar_tabla(self._tab_por_mes, "facturas_por_mes")

    def _exportar_por_estado(self) -> None:
        self._exportar_tabla(self._tab_por_estado, "facturas_por_estado")

    def _exportar_detalle_llantas(self) -> None:
        self._exportar_tabla(self._tab_detalle_llantas, "detalle_llantas")