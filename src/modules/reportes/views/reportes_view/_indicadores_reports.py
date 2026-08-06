"""Métodos de la pestaña Indicadores del ReportesView."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.modules.reportes.services.reporte_service import ReporteService
from src.modules.reportes.views.reportes_view._report_tab import _ReportTab


class _IndicadoresReportView:
    """Sección de indicadores administrativos (KPIs, estado, top clientes)."""

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
            lbl = QLabel(key)
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