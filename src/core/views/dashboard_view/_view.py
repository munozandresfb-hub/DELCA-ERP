from PySide6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.core.services.dashboard_service import (
    obtener_metricas,
    obtener_metricas_estados,
)
from src.core.services.kpi_service import KpiService
from src.core.views.dashboard_view._cards import _MetricCard, _EstadoCard


class DashboardView(QWidget):
    """Main dashboard with KPI cards, activity feed, and state breakdown."""

    def __init__(self, user) -> None:
        super().__init__()
        self.user = user
        self._build_ui()
        self._cargar_datos()

    def _build_ui(self) -> None:
        # Scroll area for the whole dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        self._main_layout = QVBoxLayout(container)
        self._main_layout.setSpacing(20)
        self._main_layout.setContentsMargins(24, 20, 24, 20)

        # =========================================================
        # Header row
        # =========================================================
        header = QHBoxLayout()

        title = QLabel("Dashboard")
        title.setStyleSheet(
            "font-size: 24px; font-weight: 700; color: #3498db;"
        )
        header.addWidget(title)

        header.addStretch()

        user_label = QLabel(f"👤 {self.user.nombre}")
        user_label.setStyleSheet(
            "font-size: 13px; color: #7f8c8d; padding: 6px 12px;"
            "background: #f8f9fa; border-radius: 6px;"
        )
        header.addWidget(user_label)

        self._btn_refresh = QPushButton("🔄 Actualizar")
        self._btn_refresh.setStyleSheet(
            """
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2471a3;
            }
            """
        )
        self._btn_refresh.clicked.connect(self._cargar_datos)
        header.addWidget(self._btn_refresh)

        self._main_layout.addLayout(header)

        # =========================================================
        # KPI Cards row
        # =========================================================
        self._cards_layout = QHBoxLayout()
        self._cards_layout.setSpacing(14)
        self._main_layout.addLayout(self._cards_layout)

        # =========================================================
        # Section: Llantas por estado
        # =========================================================
        estado_section = QVBoxLayout()
        estado_section.setSpacing(10)

        estado_title = QLabel("Llantas por Estado")
        estado_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #3498db;"
            "padding-top: 8px;"
        )
        estado_section.addWidget(estado_title)

        self._estados_layout = QHBoxLayout()
        self._estados_layout.setSpacing(10)
        self._estados_layout.addStretch()
        estado_section.addLayout(self._estados_layout)

        self._main_layout.addLayout(estado_section)

        # =========================================================
        # Section: KPI
        # =========================================================
        kpi_section = QVBoxLayout()
        kpi_section.setSpacing(10)

        kpi_header = QHBoxLayout()
        kpi_title = QLabel("KPI")
        kpi_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #3498db;"
            "padding-top: 8px;"
        )
        kpi_header.addWidget(kpi_title)
        kpi_header.addStretch()

        # Botón Ver Históricos
        self._btn_kpi_historicos = QPushButton("📈 Ver Históricos")
        self._btn_kpi_historicos.setStyleSheet(
            """
            QPushButton {
                background-color: #2c3e50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #34495e;
            }
            """
        )
        self._btn_kpi_historicos.clicked.connect(self._abrir_historicos)
        kpi_header.addWidget(self._btn_kpi_historicos)

        # Botón de crear/modificar KPI (solo admin)
        self._btn_kpi_config = QPushButton("⚙️ Crear / Modificar KPI")
        self._btn_kpi_config.setStyleSheet(
            """
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            """
        )
        es_admin = getattr(self.user, "rol_id", None) == 1
        self._btn_kpi_config.setEnabled(es_admin)
        self._btn_kpi_config.clicked.connect(self._abrir_config_kpi)
        kpi_header.addWidget(self._btn_kpi_config)

        kpi_section.addLayout(kpi_header)

        # KPI cards: 2 rows (3 + 2)
        self._kpi_row1_layout = QHBoxLayout()
        self._kpi_row1_layout.setSpacing(14)
        kpi_section.addLayout(self._kpi_row1_layout)

        self._kpi_row2_layout = QHBoxLayout()
        self._kpi_row2_layout.setSpacing(14)
        kpi_section.addLayout(self._kpi_row2_layout)

        self._main_layout.addLayout(kpi_section)

        # =========================================================
        # Section: Gráficos
        # =========================================================
        charts_section = QVBoxLayout()
        charts_section.setSpacing(10)

        charts_title = QLabel("Gráficos")
        charts_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #3498db;"
            "padding-top: 8px;"
        )
        charts_section.addWidget(charts_title)

        # Bar chart container (full width)
        bar_container = QWidget()
        bar_container.setMinimumHeight(350)
        bar_layout = QVBoxLayout(bar_container)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        self._bar_chart_view = QChartView()
        self._bar_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_owned: QChart | None = None
        bar_layout.addWidget(self._bar_chart_view)
        charts_section.addWidget(bar_container)
        self._main_layout.addLayout(charts_section)

        self._main_layout.addStretch()

        scroll.setWidget(container)

        # Main outer layout
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.setLayout(outer)

    def _cargar_datos(self) -> None:
        """Refresh all dashboard data."""
        metrics = obtener_metricas()
        self._render_cards(metrics)
        self._render_estados()
        self._render_kpi()
        self._render_charts()

    def _render_cards(self, metrics: dict) -> None:
        """Rebuild the top metric cards row (6 cards)."""
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = [
            (
                "Clientes",
                f"{metrics['clientes_activos']} / {metrics['clientes_totales']}",
                "#2ecc71",
                "🏢",
            ),
            (
                "Reencauchada en Planta",
                str(metrics["en_planta"]),
                "#3498db",
                "⚙️",
            ),
            (
                "Aptas+Pendiente",
                str(metrics["en_produccion"]),
                "#e67e22",
                "🔧",
            ),
            (
                "Entregadas del Mes",
                str(metrics["entregadas_mes"]),
                "#1abc9c",
                "✅",
            ),
            (
                "Fact. del Mes",
                f"${metrics['facturacion_mes']:,.0f}",
                "#9b59b6",
                "💰",
            ),
            (
                "Cartera Pend.",
                f"${metrics['cartera_pendiente']:,.0f}",
                "#e74c3c",
                "📋",
            ),
        ]

        for titulo, valor, color, icono in cards:
            card = _MetricCard(titulo, valor, color, icono)
            self._cards_layout.addWidget(card)

    def _render_estados(self) -> None:
        """Rebuild the three state metric cards."""
        while self._estados_layout.count():
            item = self._estados_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        estados = obtener_metricas_estados()

        state_cards = [
            (
                "Llantas en Proceso",
                str(estados["en_proceso"]),
                "#f39c12",
                "🔄",
                "Llantas actualmente en proceso de producción",
            ),
            (
                "Llantas en Planta",
                str(estados["en_planta"]),
                "#3498db",
                "🏭",
                "Reencauchadas terminadas no retiradas",
            ),
            (
                "Rechazadas",
                f"{estados['rechazadas_mes']} / {estados['rechazadas_total']}",
                "#e74c3c",
                "⚠️",
                "Rechazadas del mes / total en planta",
            ),
            (
                "Reparaciones",
                str(estados["reparaciones"]),
                "#8e44ad",
                "🔧",
                "Llantas reparadas en planta",
            ),
        ]

        for titulo, valor, color, icono, desc in state_cards:
            card = _EstadoCard(titulo, valor, color, icono, desc)
            self._estados_layout.addWidget(card)

        self._estados_layout.addStretch()

    def _render_kpi(self) -> None:
        """Render 5 KPI cards across two rows."""
        # Clear both rows
        for layout in (self._kpi_row1_layout, self._kpi_row2_layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        try:
            kpi = KpiService.obtener_actual_con_config()
        except Exception:
            label = QLabel("Error al cargar KPI")
            label.setStyleSheet("color: #e74c3c; font-size: 13px; padding: 8px;")
            self._kpi_row1_layout.addWidget(label)
            return

        # ── Row 1: Producción | Facturación | Retiro ──

        # KPI 1: Producción vs Punto de Equilibrio
        prod_color = "#2ecc71" if kpi["produccion_ok"] else "#e74c3c"
        prod_val = f"{kpi['llantas_producidas']} / {kpi['punto_equilibrio_produccion']}"
        self._kpi_row1_layout.addWidget(
            self._build_kpi_card("🛞 Producción del Mes", prod_val,
                                 f"{kpi['pct_produccion']}% de meta", prod_color)
        )

        # KPI 2: Facturación vs Punto de Equilibrio
        fin_color = "#2ecc71" if kpi["financiero_ok"] else "#e74c3c"
        fin_val = f"${kpi['facturacion_total']:,.0f} / ${kpi['punto_equilibrio_financiero']:,.0f}"
        self._kpi_row1_layout.addWidget(
            self._build_kpi_card("💰 Facturación del Mes", fin_val,
                                 f"{kpi['pct_financiero']}% de meta", fin_color)
        )

        # KPI 3: Retiradas / Producidas
        ret_color = "#2ecc71" if kpi["retiradas_mes"] >= kpi["llantas_producidas"] else "#f39c12"
        ret_val = f"{kpi['retiradas_mes']} / {kpi['llantas_producidas']}"
        self._kpi_row1_layout.addWidget(
            self._build_kpi_card("📦 Retiro del Mes", ret_val,
                                 f"{kpi['pct_retiro']}% retirado vs producido", ret_color)
        )

        # ── Row 2: Recompra | Conversión ──

        # KPI 4: Clientes que regresan / Clientes llamados
        rep_color = "#2ecc71" if kpi.get("pct_recompra", 0) >= 50 else "#f39c12"
        rep_val = f"{kpi['clientes_regresan']} / {kpi['clientes_llamados']}"
        self._kpi_row2_layout.addWidget(
            self._build_kpi_card("🏆 Recompra de Clientes", rep_val,
                                 f"{kpi['pct_recompra']}% regresan", rep_color)
        )

        # KPI 5: Producidas / Recibidas
        conv_color = "#2ecc71" if kpi.get("pct_conversion", 0) >= 80 else "#f39c12"
        conv_val = f"{kpi['llantas_producidas']} / {kpi['recibidas_mes']}"
        self._kpi_row2_layout.addWidget(
            self._build_kpi_card("🔄 Tasa de Conversión", conv_val,
                                 f"{kpi['pct_conversion']}% producidas vs recibidas", conv_color)
        )

    def _build_kpi_card(self, titulo: str, valor: str, subtitulo: str, color: str) -> QFrame:
        """Build a KPI card widget."""
        card = QFrame()
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e8ecf0;
                border-left: 4px solid {color};
            }}
            """
        )
        card.setMinimumSize(280, 100)
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        title_lbl = QLabel(titulo)
        title_lbl.setStyleSheet("font-size: 13px; color: #7f8c8d; font-weight: 500;")
        layout.addWidget(title_lbl)

        val_lbl = QLabel(valor)
        val_lbl.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {color};")
        layout.addWidget(val_lbl)

        sub_lbl = QLabel(subtitulo)
        sub_lbl.setStyleSheet("font-size: 12px; color: #95a5a6;")
        layout.addWidget(sub_lbl)

        card.setLayout(layout)
        return card

    def _abrir_config_kpi(self) -> None:
        """Open KPI configuration dialog (admin only)."""
        from src.core.views.kpi_config_dialog import KpiConfigDialog
        dialog = KpiConfigDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._render_kpi()

    def _abrir_historicos(self) -> None:
        """Open KPI historical dialog with chart."""
        from src.core.views.kpi_historico_dialog import KpiHistoricoDialog
        dialog = KpiHistoricoDialog(self)
        dialog.exec()

    def _render_charts(self) -> None:
        """Render bar chart (5 meses de facturación)."""
        try:
            self._render_bar_chart()
        except Exception as e:
            print(f"[Dashboard] Error en gráficos: {e}")

    def _delete_old_chart(self) -> None:
        """Elimina SOLO el chart creado por este dashboard.

        NUNCA se elimina el chart interno por defecto de QChartView (existe
        incluso sin setChart): eliminarlo deja la scene del view dañada y
        provoca access violation al redimensionar/maximizar la ventana.
        """
        if self._chart_owned is not None:
            self._chart_owned.deleteLater()
            self._chart_owned = None

    def _render_bar_chart(self) -> None:
        self._delete_old_chart()
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        from sqlalchemy import func
        from src.database.engine import get_session
        from src.modules.finanzas.models.factura_model import Factura

        # Calculate date range: last 5 completed months + current partial month
        now = datetime.now()
        fin = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        inicio = fin - relativedelta(months=4)

        with get_session() as session:
            results = (
                session.query(
                    func.strftime("%Y-%m", Factura.fecha_emision),
                    func.sum(Factura.total),
                )
                .filter(Factura.fecha_emision >= inicio)
                .group_by(func.strftime("%Y-%m", Factura.fecha_emision))
                .order_by(func.strftime("%Y-%m", Factura.fecha_emision))
                .all()
            )

        if not results:
            return

        bar_set = QBarSet("Facturación")
        bar_set.setColor(QColor("#3498db"))
        categories = []
        max_total = 0
        for mes_str, total in results:
            bar_set.append(float(total or 0))
            label = mes_str[5:7] + "/" + mes_str[2:4]
            categories.append(label)
            max_total = max(max_total, float(total or 0))

        series = QBarSeries()
        series.append(bar_set)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Facturación Mensual — Últimos 5 meses ($)")
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)

        chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        axis_y = QValueAxis()
        axis_y.setTitleText("$")

        axis_y.setRange(0, max_total * 1.15)
        chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(False)
        chart.setBackgroundRoundness(12)
        self._bar_chart_view.setChart(chart)
        self._chart_owned = chart