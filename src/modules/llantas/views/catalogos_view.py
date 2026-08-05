"""
Catalogs Master Data: brands, dimensions, tread designs, and rejection causes.

Provides a single unified dialog (CatalogoMaestroDialog) with 4 tabs.
Reuses LlantaService CRUD methods.
"""

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.llantas.services.llanta_service import LlantaService


# ═════════════════════════════════════════════════════════════════════
#  Table helper widget (inline, no dependency on inventario_view)
# ═════════════════════════════════════════════════════════════════════

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


# ═════════════════════════════════════════════════════════════════════
#  Inline form dialogs (one per entity)
# ═════════════════════════════════════════════════════════════════════

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


# ═════════════════════════════════════════════════════════════════════
#  Main catalog dialog
# ═════════════════════════════════════════════════════════════════════

class CatalogoMaestroDialog(QDialog):
    """Unified dialog with 4 tabs for master catalogs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Catálogos Maestros")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # Tab 1 — Marcas
        self.tab_marcas = _TablaCatalogo(["ID", "Nombre", "Siglas"], [40, 200, 100])
        tabs.addTab(self.tab_marcas, "Marcas")
        self.tab_marcas.btn_add.clicked.connect(self._add_marca)
        self.tab_marcas.btn_edit.clicked.connect(self._edit_marca)
        self.tab_marcas.btn_delete.clicked.connect(self._delete_marca)

        # Tab 2 — Dimensiones
        self.tab_dimensiones = _TablaCatalogo(
            ["ID", "Ancho", "Perfil", "Rin", "Display"],
            [40, 80, 80, 60, 200],
        )
        tabs.addTab(self.tab_dimensiones, "Dimensiones")
        self.tab_dimensiones.btn_add.clicked.connect(self._add_dimension)
        self.tab_dimensiones.btn_edit.clicked.connect(self._edit_dimension)
        self.tab_dimensiones.btn_delete.clicked.connect(self._delete_dimension)

        # Tab 3 — Diseños
        self.tab_disenos = _TablaCatalogo(
            ["ID", "Nombre", "Tipo"],
            [40, 250, 120],
        )
        tabs.addTab(self.tab_disenos, "Diseños de Banda")
        self.tab_disenos.btn_add.clicked.connect(self._add_diseno)
        self.tab_disenos.btn_edit.clicked.connect(self._edit_diseno)
        self.tab_disenos.btn_delete.clicked.connect(self._delete_diseno)

        # Tab 4 — Causas de Rechazo
        self.tab_causas = _TablaCatalogo(
            ["Código", "Descripción"],
            [150, 350],
        )
        tabs.addTab(self.tab_causas, "Causas de Rechazo")
        self.tab_causas.btn_add.clicked.connect(self._add_causa)
        self.tab_causas.btn_edit.clicked.connect(self._edit_causa)
        self.tab_causas.btn_delete.clicked.connect(self._delete_causa)

        layout.addWidget(tabs)

        # Close button
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setStyleSheet(
            "QPushButton { padding: 8px 20px; font-weight: bold; }"
        )
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

        # Load all data
        self._recargar_todo()

    # ── Load ──────────────────────────────────────────────────────────

    def _recargar_todo(self) -> None:
        self._cargar_marcas()
        self._cargar_dimensiones()
        self._cargar_disenos()
        self._cargar_causas()

    def _cargar_marcas(self) -> None:
        self.tab_marcas.limpiar()
        for m in LlantaService.listar_marcas():
            self.tab_marcas.agregar_fila(
                [str(m.id), m.nombre, m.siglas or ""], m.id
            )

    def _cargar_dimensiones(self) -> None:
        self.tab_dimensiones.limpiar()
        for m in LlantaService.listar_dimensiones():
            self.tab_dimensiones.agregar_fila(
                [str(m.id), str(m.ancho), str(m.perfil) if m.perfil is not None else "-", str(m.rin) if m.rin is not None else "-", m.display], m.id
            )

    def _cargar_disenos(self) -> None:
        self.tab_disenos.limpiar()
        for d in LlantaService.listar_disenos():
            self.tab_disenos.agregar_fila(
                [str(d.id), d.nombre, d.tipo], d.id
            )

    def _cargar_causas(self) -> None:
        self.tab_causas.limpiar()
        for c in LlantaService.listar_causas_rechazo():
            self.tab_causas.agregar_fila(
                [c.codigo, c.descripcion], c.id
            )

    # ── Marcas CRUD ───────────────────────────────────────────────────

    def _add_marca(self) -> None:
        dlg = _MarcaForm(self)
        if dlg.exec() != QDialog.Accepted:
            return
        ok, msg = LlantaService.crear_marca(dlg.valor_nombre, dlg.valor_siglas)
        if ok:
            self._cargar_marcas()
            self._cargar_disenos()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _edit_marca(self) -> None:
        pk = self.tab_marcas.fila_id()
        if pk is None:
            return
        marca = next((m for m in LlantaService.listar_marcas() if m.id == pk), None)
        if not marca:
            return
        dlg = _MarcaForm(self, marca.nombre, marca.siglas or "")
        if dlg.exec() != QDialog.Accepted:
            return
        ok, msg = LlantaService.actualizar_marca(pk, dlg.valor_nombre, dlg.valor_siglas)
        if ok:
            self._cargar_marcas()
            self._cargar_disenos()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _delete_marca(self) -> None:
        pk = self.tab_marcas.fila_id()
        if pk is None:
            return
        if QMessageBox.question(
            self, "Confirmar", "¿Eliminar esta marca?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        ok, msg = LlantaService.eliminar_marca(pk)
        if ok:
            self._cargar_marcas()
        else:
            QMessageBox.warning(self, "Error", msg)

    # ── Dimensiones CRUD ─────────────────────────────────────────────

    @staticmethod
    def _parse_rin(text: str) -> int | float:
        """Parse rin text — return float if it contains '.', else int."""
        cleaned = text.strip()
        return float(cleaned) if "." in cleaned else int(cleaned)

    @staticmethod
    def _perfil_form(dlg: _DimensionForm) -> int | None:
        """Perfil del formulario.

        Con el filtro de rin en '-' el valor del campo Rin se interpreta
        como el segundo número de la nomenclatura convencional (p.ej.
        700-16: ancho=700, rin=16, filtro '-' -> perfil=16, rin=None).
        El perfil explícito siempre tiene prioridad.
        """
        perfil = int(dlg.perfil.text()) if dlg.perfil.text().strip() else None
        if perfil is not None:
            return perfil
        if not dlg.rin_es_activo:
            texto = dlg.rin.text().strip()
            if texto and "." not in texto:
                return int(texto)
        return None

    def _add_dimension(self) -> None:
        dlg = _DimensionForm(self, nueva=True)
        if dlg.exec() != QDialog.Accepted:
            return
        if dlg.rin_es_activo and not dlg.rin.text().strip():
            QMessageBox.warning(self, "Error", "Ingrese el valor del rin o seleccione '-'")
            return
        if not dlg.rin_es_activo and dlg.rin.text().strip() and "." in dlg.rin.text().strip():
            QMessageBox.warning(self, "Error", "Con el filtro '-' el segundo número debe ser entero (p.ej. 16 en 700-16)")
            return
        ancho = int(dlg.ancho.text())
        perfil = self._perfil_form(dlg)
        rin = dlg.valor_rin
        ok, msg = LlantaService.crear_dimension(ancho, perfil, rin)
        if ok:
            self._cargar_dimensiones()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _edit_dimension(self) -> None:
        pk = self.tab_dimensiones.fila_id()
        if pk is None:
            return
        m = next((x for x in LlantaService.listar_dimensiones() if x.id == pk), None)
        if not m:
            return
        dlg = _DimensionForm(self, m.ancho, m.perfil, m.rin)
        if dlg.exec() != QDialog.Accepted:
            return
        if dlg.rin_es_activo and not dlg.rin.text().strip():
            QMessageBox.warning(self, "Error", "Ingrese el valor del rin o seleccione '-'")
            return
        if not dlg.rin_es_activo and dlg.rin.text().strip() and "." in dlg.rin.text().strip():
            QMessageBox.warning(self, "Error", "Con el filtro '-' el segundo número debe ser entero (p.ej. 16 en 700-16)")
            return
        ancho = int(dlg.ancho.text())
        perfil = self._perfil_form(dlg)
        rin = dlg.valor_rin
        ok, msg = LlantaService.actualizar_dimension(pk, ancho, perfil, rin)
        if ok:
            self._cargar_dimensiones()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _delete_dimension(self) -> None:
        pk = self.tab_dimensiones.fila_id()
        if pk is None:
            return
        if QMessageBox.question(
            self, "Confirmar", "¿Eliminar esta dimensión?\nSe verificará si hay dependencias.",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        ok, msg = LlantaService.eliminar_dimension(pk)
        if ok:
            self._cargar_dimensiones()
        else:
            QMessageBox.warning(self, "Error", msg)

    # ── Diseños CRUD ──────────────────────────────────────────────────

    def _add_diseno(self) -> None:
        dlg = _DisenoForm(self)
        if dlg.exec() != QDialog.Accepted:
            return
        ok, msg = LlantaService.crear_diseno(dlg.valor_nombre, dlg.valor_tipo)
        if ok:
            self._cargar_disenos()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _edit_diseno(self) -> None:
        pk = self.tab_disenos.fila_id()
        if pk is None:
            return
        d = next((x for x in LlantaService.listar_disenos() if x.id == pk), None)
        if not d:
            return
        dlg = _DisenoForm(self, d.nombre, d.tipo)
        if dlg.exec() != QDialog.Accepted:
            return
        ok, msg = LlantaService.actualizar_diseno(pk, dlg.valor_nombre, dlg.valor_tipo)
        if ok:
            self._cargar_disenos()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _delete_diseno(self) -> None:
        pk = self.tab_disenos.fila_id()
        if pk is None:
            return
        if QMessageBox.question(
            self, "Confirmar", "¿Eliminar este diseño?\nSe verificará si hay dependencias.",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        ok, msg = LlantaService.eliminar_diseno(pk)
        if ok:
            self._cargar_disenos()
        else:
            QMessageBox.warning(self, "Error", msg)

    # ── Causas CRUD ───────────────────────────────────────────────────

    def _add_causa(self) -> None:
        dlg = _CausaForm(self)
        if dlg.exec() != QDialog.Accepted:
            return
        ok, msg = LlantaService.crear_causa_rechazo(
            dlg.codigo.text().strip(),
            dlg.descripcion.text().strip(),
        )
        if ok:
            self._cargar_causas()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _edit_causa(self) -> None:
        pk = self.tab_causas.fila_id()
        if pk is None:
            return
        c = next((x for x in LlantaService.listar_causas_rechazo() if x.id == pk), None)
        if not c:
            return
        dlg = _CausaForm(self, c.codigo, c.descripcion)
        if dlg.exec() != QDialog.Accepted:
            return
        ok, msg = LlantaService.actualizar_causa_rechazo(
            pk,
            dlg.codigo.text().strip(),
            dlg.descripcion.text().strip(),
        )
        if ok:
            self._cargar_causas()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _delete_causa(self) -> None:
        pk = self.tab_causas.fila_id()
        if pk is None:
            return
        if QMessageBox.question(
            self, "Confirmar", "¿Eliminar esta causa de rechazo?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        ok, msg = LlantaService.eliminar_causa_rechazo(pk)
        if ok:
            self._cargar_causas()
        else:
            QMessageBox.warning(self, "Error", msg)


# ═════════════════════════════════════════════════════════════════════
#  Page wrapper for sidebar navigation
# ═════════════════════════════════════════════════════════════════════


class CatalogosPage(QWidget):
    """Sidebar page wrapper that opens CatalogoMaestroDialog."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("Catálogos Maestros")
        title.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #2c3e50;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "Gestione marcas, dimensiones, diseños de banda\n"
            "y causas de rechazo desde un solo lugar."
        )
        desc.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        btn = QPushButton("Abrir Catálogos Maestros")
        btn.setStyleSheet(
            "QPushButton {"
            "  background: #3498db; color: white;"
            "  padding: 14px 40px; font-size: 16px;"
            "  border-radius: 8px; font-weight: bold;"
            "}"
            "QPushButton:hover { background: #2980b9; }"
        )
        btn.clicked.connect(self._abrir)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _abrir(self) -> None:
        dlg = CatalogoMaestroDialog(self)
        dlg.exec()
