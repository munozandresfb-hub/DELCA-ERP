"""Widgets reutilizables de la vista de inventario: tarjetas KPI, tabla CRUD y colores."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# ── Colores ──────────────────────────────────────────────────────────
C_AZUL = "#3498db"
C_AZUL_OSCURO = "#2980b9"
C_VERDE = "#27ae60"
C_AMBAR = "#f39c12"
C_ROJO = "#e74c3c"
C_BG_CARD = "#f8f9fa"

KPI_COLORS = {
    "mp": C_AZUL,
    "valor": C_AZUL,
    "capacidad": C_VERDE,
    "planta": C_AMBAR,
    "margen": C_AMBAR,
}

ANTIGUEDAD_COLORS = {
    30: QColor("#fff3cd"),    # 1 mes: amarillo
    90: QColor("#ffe0b2"),    # 3 meses: naranja claro
    180: QColor("#ffccbc"),   # 6 meses: naranja intenso
    365: QColor("#ffcdd2"),   # 12 meses: rojo claro
}


def _color_antiguedad(dias: int) -> QColor | None:
    if dias >= 365:
        return QColor("#e57373")  # rojo intenso
    if dias >= 180:
        return QColor("#ffccbc")
    if dias >= 90:
        return QColor("#ffe0b2")
    if dias >= 30:
        return QColor("#fff3cd")
    return None


# ═════════════════════════════════════════════════════════════════════
#  KPI Card Widget
# ═════════════════════════════════════════════════════════════════════

class _KpiCard(QFrame):
    """Single KPI metric card."""

    def __init__(self, titulo: str, valor: str, color: str, tooltip: str = "") -> None:
        super().__init__()
        self.setStyleSheet(
            f"""
            _KpiCard {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                border-top: 4px solid {color};
            }}
            """
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)

        self._valor_label = QLabel(valor)
        self._valor_label.setStyleSheet(
            f"font-size: 22px; font-weight: bold; color: {color};"
        )
        layout.addWidget(self._valor_label)

        self._titulo_label = QLabel(titulo)
        self._titulo_label.setStyleSheet(
            "font-size: 11px; color: #777; font-weight: 600;"
        )
        layout.addWidget(self._titulo_label)

        self.setLayout(layout)
        self.setMinimumWidth(150)
        if tooltip:
            self.setToolTip(tooltip)

    def actualizar(self, valor: str) -> None:
        self._valor_label.setText(valor)


# ═════════════════════════════════════════════════════════════════════
#  Generic CRUD table widget
# ═════════════════════════════════════════════════════════════════════

class _CrudTableWidget(QWidget):
    """Generic CRUD table with add/edit/delete."""

    def __init__(
        self,
        columnas: list[str],
        ancho_cols: list[int] | None = None,
    ) -> None:
        super().__init__()
        self._columnas = columnas
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(len(columnas))
        self.table.setHorizontalHeaderLabels(columnas)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        if ancho_cols:
            for i, w in enumerate(ancho_cols):
                self.table.setColumnWidth(i, w)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ Agregar")
        self.btn_add.setStyleSheet(
            f"QPushButton {{ background: {C_VERDE}; color: white; padding: 6px 16px; "
            f"border-radius: 4px; font-weight: bold; }}"
        )
        self.btn_edit = QPushButton("Editar")
        self.btn_edit.setStyleSheet(
            f"QPushButton {{ background: {C_AZUL}; color: white; padding: 6px 16px; "
            f"border-radius: 4px; font-weight: bold; }}"
        )
        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setStyleSheet(
            f"QPushButton {{ background: {C_ROJO}; color: white; padding: 6px 16px; "
            f"border-radius: 4px; font-weight: bold; }}"
        )
        self.btn_import = QPushButton("📥 Importar Excel")
        self.btn_import.setStyleSheet(
            "QPushButton { background: #6c757d; color: white; padding: 6px 16px; "
            "border-radius: 4px; font-weight: bold; }"
        )
        self.btn_import.setVisible(False)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_delete)
        btn_row.addWidget(self.btn_import)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def limpiar(self) -> None:
        self.table.setRowCount(0)

    def agregar_fila(self, valores: list[str], datos_id: int) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, val in enumerate(valores):
            item = QTableWidgetItem(val)
            if col == 0:
                item.setData(Qt.ItemDataRole.UserRole, datos_id)
            self.table.setItem(row, col, item)

    def fila_seleccionada(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None