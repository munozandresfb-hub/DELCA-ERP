from PySide6.QtCharts import QChart, QChartView, QLineSeries, QScatterSeries, QValueAxis, QCategoryAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.core.services.kpi_service import KpiService


class KpiHistoricoDialog(QDialog):
    """Dialog showing historical KPI records with behavior chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Histórico de KPI")
        self.resize(800, 600)
        self._data = KpiService.obtener_historicos()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()

        title = QLabel("Comportamiento Histórico de KPI")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #2c3e50;")
        layout.addWidget(title)
        layout.addSpacing(8)

        # Toggle button for switching between production and financial chart
        btn_row = QHBoxLayout()
        self._btn_prod = QPushButton("🛞 Producción")
        self._btn_prod.setStyleSheet(self._btn_style("#3498db"))
        self._btn_prod.clicked.connect(lambda: self._render_chart("produccion"))
        btn_row.addWidget(self._btn_prod)

        self._btn_fin = QPushButton("💰 Facturación")
        self._btn_fin.setStyleSheet(self._btn_style("#9b59b6"))
        self._btn_fin.clicked.connect(lambda: self._render_chart("financiero"))
        btn_row.addWidget(self._btn_fin)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Chart view
        self._chart_view = QChartView()
        self._chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._chart_view.setMinimumHeight(280)
        self._chart_owned: QChart | None = None
        layout.addWidget(self._chart_view)

        # Table
        table_label = QLabel("Registros Mensuales")
        table_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #2c3e50; padding-top: 8px;")
        layout.addWidget(table_label)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Período", "Llantas Producidas", "Facturación", "Cumplimiento"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._poblar_tabla()
        layout.addWidget(self._table)

        # Close button
        close_btn = QPushButton("Cerrar")
        close_btn.setStyleSheet(
            "QPushButton { background-color: #95a5a6; color: white; border: none; "
            "border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { background-color: #7f8c8d; }"
        )
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)

        # Default chart: production
        self._render_chart("produccion")

    def _btn_style(self, color: str) -> str:
        return (
            f"QPushButton {{ background-color: {color}; color: white; border: none; "
            f"border-radius: 6px; padding: 6px 16px; font-size: 12px; font-weight: 600; }}"
        )

    def _poblar_tabla(self) -> None:
        config = KpiService.obtener_config()
        pp = config.punto_equilibrio_produccion if config else 100
        pf = float(config.punto_equilibrio_financiero) if config else 1000000.0

        self._table.setRowCount(len(self._data))
        for i, r in enumerate(self._data):
            self._table.setItem(i, 0, QTableWidgetItem(r["periodo"]))

            item_prod = QTableWidgetItem(str(r["llantas_producidas"]))
            item_prod.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 1, item_prod)

            item_fin = QTableWidgetItem(f"${r['facturacion_total']:,.0f}")
            item_fin.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 2, item_fin)

            pct_p = round((r["llantas_producidas"] / pp) * 100, 1) if pp > 0 else 0
            ok = "✅" if r["llantas_producidas"] >= pp else "⚠️"
            item_cumpl = QTableWidgetItem(f"{ok} {pct_p}%")
            item_cumpl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 3, item_cumpl)

    def _delete_old_chart(self) -> None:
        """Elimina SOLO el chart creado por este diálogo (nunca el default de QChartView)."""
        if self._chart_owned is not None:
            self._chart_owned.deleteLater()
            self._chart_owned = None

    def _render_chart(self, modo: str) -> None:
        """Render historical line chart for production or financial KPI."""
        if not self._data:
            return

        try:
            self._delete_old_chart()

            config = KpiService.obtener_config()
            pp = config.punto_equilibrio_produccion if config else 100
            pf = float(config.punto_equilibrio_financiero) if config else 1000000.0

            # Reverse to chronological order
            data = list(reversed(self._data))

            series = QLineSeries()
            series.setName("Llantas Producidas" if modo == "produccion" else "Facturación")
            series.setColor(QColor("#3498db") if modo == "produccion" else QColor("#9b59b6"))
            series.setPen(series.pen())

            # Scatter points
            scatter = QScatterSeries()
            scatter.setMarkerSize(10)
            scatter.setColor(QColor("#3498db") if modo == "produccion" else QColor("#9b59b6"))
            scatter.setBorderColor(QColor("#2c3e50"))

            max_val = 0
            categories = []
            for i, r in enumerate(data):
                val = r["llantas_producidas"] if modo == "produccion" else r["facturacion_total"]
                series.append(float(i), float(val))
                scatter.append(float(i), float(val))
                max_val = max(max_val, float(val))
                categories.append(r["periodo"])

            # Break-even line
            equilibrio = pp if modo == "produccion" else pf
            eq_series = QLineSeries()
            eq_series.setName("Punto de Equilibrio")
            eq_series.setColor(QColor("#e74c3c"))
            pen = eq_series.pen()
            pen.setStyle(Qt.PenStyle.DashLine)
            eq_series.setPen(pen)
            eq_series.append(0.0, float(equilibrio))
            eq_series.append(float(len(data) - 1), float(equilibrio))
            max_val = max(max_val, float(equilibrio) * 1.2)

            chart = QChart()
            chart.addSeries(series)
            chart.addSeries(scatter)
            chart.addSeries(eq_series)
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            chart.setBackgroundRoundness(12)

            if modo == "produccion":
                chart.setTitle("Histórico: Llantas Producidas vs Punto de Equilibrio")
            else:
                chart.setTitle("Histórico: Facturación vs Punto de Equilibrio")

            chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

            # X axis (categories)
            axis_x = QCategoryAxis()
            axis_x.append(categories[0], 0.0)
            step = max(1, len(categories) // 6)
            for i in range(step, len(categories), step):
                axis_x.append(categories[i], float(i))
            if len(categories) > 1:
                axis_x.append(categories[-1], float(len(categories) - 1))
            axis_x.setLabelsPosition(QCategoryAxis.AxisLabelsPosition.AxisLabelsPositionOnValue)
            axis_x.setGridLineVisible(False)
            axis_x.setRange(-0.5, float(len(data) - 1) + 0.5)
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axis_x)
            scatter.attachAxis(axis_x)
            eq_series.attachAxis(axis_x)

            # Y axis
            axis_y = QValueAxis()
            axis_y.setTitleText("Unidades" if modo == "produccion" else "$")
            axis_y.setRange(0, max_val)
            axis_y.setLabelFormat("%.0f" if modo == "produccion" else "$%.0f")
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_y)
            scatter.attachAxis(axis_y)
            eq_series.attachAxis(axis_y)

            self._chart_view.setChart(chart)
            self._chart_owned = chart
        except Exception:
            pass
