from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.clientes.models.cliente_model import Cliente
from src.modules.clientes.services.cliente_service import ClienteService
from src.modules.clientes.viewmodels.cliente_viewmodel import ClienteViewModel


import logging

logger = logging.getLogger("delca.views")
class ClienteFormDialog(QDialog):
    """Dialog for creating or editing a client."""

    def __init__(
        self, parent: QWidget | None = None, cliente: Cliente | None = None
    ) -> None:
        super().__init__(parent)
        self.cliente = cliente
        self.setWindowTitle(
            "Editar Cliente" if cliente else "Nuevo Cliente"
        )
        self.resize(450, 400)
        self.setup_ui()
        if cliente:
            self._cargar_datos(cliente)

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        form = QFormLayout()
        form.setSpacing(12)

        input_style = "font-size: 14px; padding: 6px;"

        self.nombre_input = QLineEdit()
        self.nombre_input.setStyleSheet(input_style)
        self.nit_input = QLineEdit()
        self.nit_input.setStyleSheet(input_style)
        self.celular_input = QLineEdit()
        self.celular_input.setStyleSheet(input_style)
        self.email_input = QLineEdit()
        self.email_input.setStyleSheet(input_style)
        self.direccion_input = QLineEdit()
        self.direccion_input.setStyleSheet(input_style)
        self.ciudad_input = QLineEdit()
        self.ciudad_input.setStyleSheet(input_style)

        label_style = "font-size: 14px; font-weight: 600;"

        nombre_lbl = QLabel("Nombre *:")
        nombre_lbl.setStyleSheet(label_style)
        form.addRow(nombre_lbl, self.nombre_input)

        nit_lbl = QLabel("NIT / CC *:")
        nit_lbl.setStyleSheet(label_style)
        form.addRow(nit_lbl, self.nit_input)

        cel_lbl = QLabel("Celular:")
        cel_lbl.setStyleSheet(label_style)
        form.addRow(cel_lbl, self.celular_input)

        email_lbl = QLabel("Email:")
        email_lbl.setStyleSheet(label_style)
        form.addRow(email_lbl, self.email_input)

        dir_lbl = QLabel("Dirección:")
        dir_lbl.setStyleSheet(label_style)
        form.addRow(dir_lbl, self.direccion_input)

        ciudad_lbl = QLabel("Ciudad:")
        ciudad_lbl.setStyleSheet(label_style)
        form.addRow(ciudad_lbl, self.ciudad_input)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        guardar_btn = QPushButton("Guardar")
        guardar_btn.clicked.connect(self._guardar)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addWidget(guardar_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _cargar_datos(self, cliente: Cliente) -> None:
        self.nombre_input.setText(cliente.nombre or "")
        self.nit_input.setText(cliente.nit or "")
        self.celular_input.setText(cliente.celular or "")
        self.email_input.setText(cliente.email or "")
        self.direccion_input.setText(cliente.direccion or "")
        self.ciudad_input.setText(cliente.ciudad or "")

    def _guardar(self) -> None:
        """Validate and accept."""
        nombre = self.nombre_input.text().strip()
        nit = self.nit_input.text().strip()

        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio")
            self.nombre_input.setFocus()
            return
        if not nit:
            QMessageBox.warning(self, "Validación", "El NIT / CC es obligatorio")
            self.nit_input.setFocus()
            return

        self.accept()

    def get_data(
        self,
    ) -> tuple[str, str, str, str, str, str]:
        return (
            self.nombre_input.text().strip(),
            self.nit_input.text().strip(),
            self.celular_input.text().strip(),
            self.email_input.text().strip(),
            self.direccion_input.text().strip(),
            self.ciudad_input.text().strip(),
        )


class ClientesView(QWidget):
    """Full client management view with table, search and CRUD."""

    COLUMNAS = [
        "ID", "Nombre", "NIT", "Teléfono", "Celular", "Email",
        "Ciudad", "Activo", "Llantas en Planta", "Deuda",
    ]

    def __init__(self, user=None) -> None:
        super().__init__()
        self.user = user
        self.viewmodel = ClienteViewModel()
        self._ids_en_planta: set[int] = set()
        self.setup_ui()
        try:
            self._cargar_datos()
        except Exception as e:
            logger.error(f"[ClientesView] Error al cargar datos iniciales", exc_info=True)

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # Header
        header = QLabel("Módulo Clientes")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px 0;"
        )
        layout.addWidget(header)

        # Search bar + buttons row
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)

        # Search — shorter to give space to button
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Buscar por nombre, NIT, teléfono o email..."
        )
        self.search_input.textChanged.connect(self._buscar)
        self.search_input.setMinimumWidth(200)
        self.search_input.setMaximumWidth(450)
        self.search_input.setStyleSheet(
            "font-size: 13px; padding: 8px 12px; border: 1px solid #dce1e6;"
            "border-radius: 8px;"
        )
        search_layout.addWidget(self.search_input)

        # + Nuevo Cliente — grande, azul, llamativo
        self._nuevo_btn = QPushButton("+ Nuevo Cliente")
        self._nuevo_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #3498db;
                color: white;
                font-size: 14px;
                font-weight: 700;
                padding: 10px 24px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2471a3;
            }
            """
        )
        self._nuevo_btn.clicked.connect(self._nuevo_cliente)
        search_layout.addWidget(self._nuevo_btn)

        # Editar
        self._editar_btn = QPushButton("Editar")
        self._editar_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 18px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #e67e22; }
            QPushButton:pressed { background-color: #d35400; }
            """
        )
        self._editar_btn.clicked.connect(self._editar_cliente)
        search_layout.addWidget(self._editar_btn)

        # Eliminar — solo admin
        self._eliminar_btn = QPushButton("Eliminar")
        self._eliminar_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 13px;
                font-weight: 600;
                padding: 8px 18px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #c0392b; }
            QPushButton:pressed { background-color: #a93226; }
            QPushButton:disabled { background-color: #bdc3c7; }
            """
        )
        self._eliminar_btn.clicked.connect(self._eliminar_cliente)
        es_admin = getattr(self.user, "rol_id", None) == 1 if self.user else False
        self._eliminar_btn.setEnabled(es_admin)
        search_layout.addWidget(self._eliminar_btn)

        layout.addLayout(search_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNAS))
        self.table.setHorizontalHeaderLabels(self.COLUMNAS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _cargar_datos(self) -> None:
        self.viewmodel.cargar_clientes()
        self._ids_en_planta = ClienteService.obtener_ids_con_llantas_en_planta()
        self._poblar_tabla()

    def _poblar_tabla(self) -> None:
        clientes = self.viewmodel.clientes
        self.table.setRowCount(len(clientes))

        for row, c in enumerate(clientes):
            # Col 0-7: data from model
            self.table.setItem(row, 0, QTableWidgetItem(str(c.id)))
            self.table.setItem(row, 1, QTableWidgetItem(c.nombre or ""))
            self.table.setItem(row, 2, QTableWidgetItem(c.nit or ""))
            self.table.setItem(row, 3, QTableWidgetItem(c.telefono or ""))
            self.table.setItem(row, 4, QTableWidgetItem(c.celular or ""))
            self.table.setItem(row, 5, QTableWidgetItem(c.email or ""))
            self.table.setItem(row, 6, QTableWidgetItem(c.ciudad or ""))
            self.table.setItem(
                row, 7, QTableWidgetItem("Sí" if c.activo else "No")
            )
            # Col 8: Llantas en Planta
            tiene_planta = c.id in self._ids_en_planta
            self.table.setItem(
                row, 8, QTableWidgetItem("Sí" if tiene_planta else "No")
            )
            # Col 9: Deuda
            tiene_deuda = float(c.saldo or 0) > 0
            self.table.setItem(
                row, 9, QTableWidgetItem("Sí" if tiene_deuda else "No")
            )

        # Hide ID column
        self.table.setColumnHidden(0, True)

    def _buscar(self) -> None:
        termino = self.search_input.text()
        self.viewmodel.buscar(termino)
        self._poblar_tabla()

    def _nuevo_cliente(self) -> None:
        dialog = ClienteFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        nombre, nit, celular, email, direccion, ciudad = (
            dialog.get_data()
        )

        ok, msg = self.viewmodel.crear(
            nombre=nombre,
            nit=nit,
            celular=celular or None,
            email=email or None,
            direccion=direccion or None,
            ciudad=ciudad or None,
        )

        if ok:
            self._poblar_tabla()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _editar_cliente(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Seleccionar", "Seleccione un cliente de la tabla"
            )
            return

        cliente_id = int(self.table.item(row, 0).text())
        cliente = self.viewmodel.obtener_por_id(cliente_id)
        if not cliente:
            QMessageBox.warning(self, "Error", "Cliente no encontrado")
            return

        dialog = ClienteFormDialog(self, cliente)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        nombre, nit, celular, email, direccion, ciudad = (
            dialog.get_data()
        )

        ok, msg = self.viewmodel.actualizar(
            cliente_id=cliente_id,
            nombre=nombre,
            nit=nit,
            celular=celular or None,
            email=email or None,
            direccion=direccion or None,
            ciudad=ciudad or None,
        )

        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", "Cliente actualizado")
        else:
            QMessageBox.warning(self, "Error", str(msg))

    def _eliminar_cliente(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Seleccionar", "Seleccione un cliente de la tabla"
            )
            return

        cliente_id = int(self.table.item(row, 0).text())
        cliente_nombre = self.table.item(row, 1).text()

        confirm = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Está seguro de eliminar a '{cliente_nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.viewmodel.eliminar(cliente_id)
        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)
