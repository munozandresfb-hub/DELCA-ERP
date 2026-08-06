"""Widget base de pestaña de reporte: tabla con resúmenes opcionales."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


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