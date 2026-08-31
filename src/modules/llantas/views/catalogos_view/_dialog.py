from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from src.modules.llantas.services.llanta_service import LlantaService
from src.modules.llantas.views.catalogos_view._tabular import (
    _CausaForm,
    _DimensionForm,
    _DisenoForm,
    _MarcaForm,
    _TablaCatalogo,
)


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