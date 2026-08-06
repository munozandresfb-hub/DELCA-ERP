from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class _TablaCatalogo(QWidget):
    """Generic read-only table with Add / Edit / Delete buttons."""

    def __init__(
        self,
        columnas: list[str],
        ancho_cols: list[int] | None = None,
    ) -> None:
        super().__init__()
        self._columnas = columnas
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        if ancho_cols:
            for i, w in enumerate(ancho_cols):
                self.tabla.setColumnWidth(i, w)
        layout.addWidget(self.tabla)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("+ Agregar")
        self.btn_add.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; "
            "padding: 6px 16px; border-radius: 4px; font-weight: bold; }"
        )
        self.btn_edit = QPushButton("Editar")
        self.btn_edit.setStyleSheet(
            "QPushButton { background: #3498db; color: white; "
            "padding: 6px 16px; border-radius: 4px; font-weight: bold; }"
        )
        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setStyleSheet(
            "QPushButton { background: #e74c3c; color: white; "
            "padding: 6px 16px; border-radius: 4px; font-weight: bold; }"
        )
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def limpiar(self) -> None:
        self.tabla.setRowCount(0)

    def agregar_fila(self, valores: list[str], datos_id: int) -> None:
        row = self.tabla.rowCount()
        self.tabla.insertRow(row)
        for col, val in enumerate(valores):
            item = QTableWidgetItem(val)
            if col == 0:
                item.setData(256, datos_id)  # Qt.UserRole
            self.tabla.setItem(row, col, item)

    def fila_id(self) -> int | None:
        row = self.tabla.currentRow()
        if row < 0:
            return None
        item = self.tabla.item(row, 0)
        return item.data(256) if item else None


class _MarcaForm(QDialog):
    def __init__(self, parent=None, nombre: str = "", siglas: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Marca")
        self.resize(350, 160)
        layout = QFormLayout(self)
        self.input_nombre = QLineEdit(nombre)
        self.input_nombre.setPlaceholderText("Nombre completo (ej. Goodyear)")
        layout.addRow("Nombre:", self.input_nombre)
        self.input_siglas = QLineEdit(siglas)
        self.input_siglas.setPlaceholderText("Abreviatura (ej. GY)")
        self.input_siglas.setMaxLength(10)
        layout.addRow("Siglas:", self.input_siglas)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    @property
    def valor_nombre(self) -> str:
        return self.input_nombre.text().strip()

    @property
    def valor_siglas(self) -> str:
        return self.input_siglas.text().strip()


class _DimensionForm(QDialog):
    def __init__(
        self,
        parent=None,
        ancho: int | str = "",
        perfil: int | str = "",
        rin: int | float | None = None,
        nueva: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle("Dimension")
        self.resize(350, 200)
        layout = QFormLayout(self)

        self.ancho = QLineEdit(str(ancho) if ancho else "")
        self.ancho.setPlaceholderText("Ej. 205")
        self.ancho.setValidator(QIntValidator(1, 9999, self))
        layout.addRow("Ancho (mm):", self.ancho)

        self.perfil = QLineEdit(str(perfil) if perfil else "")
        self.perfil.setPlaceholderText("Opcional (ej. 55) — dejar vacío si no aplica")
        self.perfil.setValidator(QIntValidator(1, 999, self))
        layout.addRow("Perfil:", self.perfil)

        # Rin: selector "Rin" (la dimensión tiene rin) / "-" (sin rin,
        # p.ej. llantas convencionales/antiguas como 10.00-20). El campo de
        # texto queda SIEMPRE editable; el combo decide si el valor se usa.
        self.rin_tipo = QComboBox()
        self.rin_tipo.addItem("Rin", "Rin")
        self.rin_tipo.addItem("-", "-")
        self.rin = QLineEdit()
        self.rin.setPlaceholderText("Ej. 16 o 22.5")
        self.rin.setMaxLength(4)
        self.rin.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\d{1,2}(\.\d)?$"), self)
        )
        rin_row = QHBoxLayout()
        rin_row.addWidget(self.rin_tipo)
        rin_row.addWidget(self.rin, 1)
        layout.addRow("Rin (″):", rin_row)

        if nueva:
            # La mayoría de llantas usan rin: al crear, el combo inicia en
            # "Rin" con el campo vacío listo para escribir.
            self.rin_tipo.setCurrentIndex(0)
        elif rin is None:
            self.rin_tipo.setCurrentIndex(1)  # "-"
        else:
            self.rin.setText(str(rin))

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    @property
    def rin_es_activo(self) -> bool:
        return self.rin_tipo.currentData() == "Rin"

    @property
    def valor_rin(self) -> int | float | None:
        """None si no aplica ('-'); si no, el valor numérico del campo."""
        if not self.rin_es_activo:
            return None
        text = self.rin.text().strip()
        return float(text) if "." in text else int(text)


class _DisenoForm(QDialog):
    def __init__(self, parent=None, nombre: str = "", tipo: str = "MIXTO"):
        super().__init__(parent)
        self.setWindowTitle("Diseño de Banda")
        self.resize(350, 140)
        layout = QFormLayout(self)

        self.nombre_input = QLineEdit(nombre)
        self.nombre_input.setPlaceholderText("Nombre del diseño (ej. MSA)")
        layout.addRow("Nombre:", self.nombre_input)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("Mixto", "MIXTO")
        self.tipo_combo.addItem("Tracción", "TRACCION")
        self.tipo_combo.addItem("Direccional", "DIRECCIONAL")
        idx = self.tipo_combo.findData((tipo or "").upper())
        if idx >= 0:
            self.tipo_combo.setCurrentIndex(idx)
        layout.addRow("Tipo:", self.tipo_combo)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    @property
    def valor_nombre(self) -> str:
        return self.nombre_input.text().strip()

    @property
    def valor_tipo(self) -> str:
        return self.tipo_combo.currentData()


class _CausaForm(QDialog):
    def __init__(self, parent=None, codigo: str = "", descripcion: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Causa de Rechazo")
        self.resize(400, 200)
        layout = QFormLayout(self)
        self.codigo = QLineEdit(codigo)
        self.descripcion = QLineEdit(descripcion)
        layout.addRow("Código:", self.codigo)
        layout.addRow("Descripción:", self.descripcion)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)