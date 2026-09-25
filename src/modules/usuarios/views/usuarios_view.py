"""User management view — CRUD for usuarios with RBAC role assignment."""

from PySide6.QtGui import QColor, QBrush
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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.usuarios.services.usuario_service import UsuarioService


import logging

logger = logging.getLogger("delca.views")
class PasswordResetDialog(QDialog):
    """Dialog to reset a user's password."""

    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Reset Password - {username}")
        self.setModal(True)
        self.resize(380, 200)
        self.new_password = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        msg = QLabel(
            "Ingrese la nueva contraseña para el usuario.\n"
            "Debe cumplir los requisitos de seguridad:"
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        form = QFormLayout()
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.Password)
        form.addRow("Nueva contraseña:", self.new_pass_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        form.addRow("Confirmar:", self.confirm_input)
        layout.addLayout(form)

        info = QLabel(
            "• Mínimo 8 caracteres\n"
            "• Al menos una mayúscula\n"
            "• Al menos una minúscula\n"
            "• Al menos un número\n"
            "• Al menos un carácter especial"
        )
        info.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def validate_and_accept(self):
        p1 = self.new_pass_input.text()
        p2 = self.confirm_input.text()

        if not p1:
            QMessageBox.warning(
                self, "Validación", "Ingrese la nueva contraseña"
            )
            return
        if p1 != p2:
            QMessageBox.warning(
                self, "Validación", "Las contraseñas no coinciden"
            )
            return

        from src.modules.usuarios.services.auth_service import AuthService
        valid, msg = AuthService.validate_password_strength(p1)
        if not valid:
            QMessageBox.warning(self, "Contraseña inválida", msg)
            return

        self.new_password = p1
        self.accept()


class UsuarioFormDialog(QDialog):
    """Dialog for creating or editing a user."""

    def __init__(
        self,
        parent: QWidget | None = None,
        usuario: dict | None = None,
    ) -> None:
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle(
            "Editar Usuario" if usuario else "Nuevo Usuario"
        )
        self.resize(400, 300)
        self._roles = UsuarioService.get_roles()
        self.setup_ui()
        if usuario:
            self._cargar_datos(usuario)

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        form = QFormLayout()

        self.nombre_input = QLineEdit()
        form.addRow("Nombre *:", self.nombre_input)

        self.username_input = QLineEdit()
        form.addRow("Username *:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        if not self.usuario:
            form.addRow("Contraseña *:", self.password_input)

        self.rol_combo = QComboBox()
        for r in self._roles:
            self.rol_combo.addItem(r["nombre"], r["id"])
        form.addRow("Rol *:", self.rol_combo)

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

    def _cargar_datos(self, usuario: dict) -> None:
        self.nombre_input.setText(usuario.get("nombre", ""))
        self.username_input.setText(usuario.get("username", ""))
        self.username_input.setEnabled(False)  # Don't allow username change
        # Select current role
        for i in range(self.rol_combo.count()):
            if self.rol_combo.itemData(i) == usuario.get("rol_id"):
                self.rol_combo.setCurrentIndex(i)
                break

    def _guardar(self) -> None:
        nombre = self.nombre_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        rol_id = self.rol_combo.currentData()

        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio")
            self.nombre_input.setFocus()
            return
        if not username:
            QMessageBox.warning(self, "Validación", "El username es obligatorio")
            self.username_input.setFocus()
            return

        if not self.usuario:
            # New user: password required
            if not password:
                QMessageBox.warning(
                    self, "Validación", "La contraseña es obligatoria"
                )
                self.password_input.setFocus()
                return
            from src.modules.usuarios.services.auth_service import AuthService
            valid, msg = AuthService.validate_password_strength(password)
            if not valid:
                QMessageBox.warning(self, "Contraseña inválida", msg)
                self.password_input.setFocus()
                return

        self.accept()

    def get_data(self) -> tuple:
        return (
            self.nombre_input.text().strip(),
            self.username_input.text().strip(),
            self.password_input.text(),
            self.rol_combo.currentData(),
        )


class UsuariosView(QWidget):
    """Full user management view with table, search and CRUD."""

    COLUMNAS = [
        "ID", "Nombre", "Username", "Rol",
        "Último Acceso", "Expiración", "Estado",
    ]

    def __init__(self, user) -> None:
        super().__init__()
        self._current_user = user
        self.service = UsuarioService()
        self.setup_ui()
        try:
            self._cargar_datos()
        except Exception as e:
            logger.error(f"[UsuariosView] Error al cargar datos iniciales", exc_info=True)

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # Header
        header = QLabel("Gestión de Usuarios")
        header.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 10px 0;"
        )
        layout.addWidget(header)

        # Search bar + buttons
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Buscar por nombre o username..."
        )
        self.search_input.textChanged.connect(self._buscar)
        search_layout.addWidget(self.search_input)

        nuevo_btn = QPushButton("+ Nuevo Usuario")
        nuevo_btn.clicked.connect(self._nuevo_usuario)
        search_layout.addWidget(nuevo_btn)

        editar_btn = QPushButton("Editar")
        editar_btn.clicked.connect(self._editar_usuario)
        search_layout.addWidget(editar_btn)

        reset_btn = QPushButton("Reset Password")
        reset_btn.clicked.connect(self._reset_password)
        search_layout.addWidget(reset_btn)

        desactivar_btn = QPushButton("Desactivar")
        desactivar_btn.clicked.connect(self._desactivar_usuario)
        desactivar_btn.setStyleSheet(
            "QPushButton { color: #c0392b; }"
        )
        search_layout.addWidget(desactivar_btn)

        reactivar_btn = QPushButton("Reactivar")
        reactivar_btn.clicked.connect(self._reactivar_usuario)
        reactivar_btn.setStyleSheet(
            "QPushButton { color: #27ae60; }"
        )
        search_layout.addWidget(reactivar_btn)

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
        self.usuarios = self.service.listar_usuarios()
        self._poblar_tabla()

    def _poblar_tabla(self) -> None:
        self.table.setRowCount(len(self.usuarios))

        # Color map for status
        status_colors = {
            "Expirada": "#e74c3c",
            "Cambio requerido": "#f39c12",
            "Bloqueado": "#c0392b",
            "Inactivo": "#bdc3c7",
            "Activo": "#2ecc71",
        }

        for row, u in enumerate(self.usuarios):
            self.table.setItem(
                row, 0, QTableWidgetItem(str(u["id"]))
            )
            self.table.setItem(
                row, 1, QTableWidgetItem(u["nombre"] or "")
            )
            self.table.setItem(
                row, 2, QTableWidgetItem(u["username"] or "")
            )
            self.table.setItem(
                row, 3, QTableWidgetItem(u["rol_nombre"] or "")
            )
            self.table.setItem(
                row, 4, QTableWidgetItem(u["ultimo_acceso"] or "")
            )

            # Password / account status with color
            if u["password_expired"]:
                estado = "Expirada"
            elif u["requires_password_change"]:
                estado = "Cambio requerido"
            elif u["bloqueado"]:
                estado = "Bloqueado"
            elif not u["activo"]:
                estado = "Inactivo"
            else:
                estado = "Activo"
            estado_item = QTableWidgetItem(estado)
            color = status_colors.get(estado, "#7f8c8d")
            estado_item.setForeground(QBrush(QColor(color)))
            self.table.setItem(row, 5, estado_item)

            # Active status with color
            activo_texto = "Activo" if u["activo"] else "Inactivo"
            activo_item = QTableWidgetItem(activo_texto)
            activo_color = "#2ecc71" if u["activo"] else "#e74c3c"
            activo_item.setForeground(QBrush(QColor(activo_color)))
            self.table.setItem(row, 6, activo_item)

        # Hide ID column
        self.table.setColumnHidden(0, True)

    def _buscar(self) -> None:
        termino = self.search_input.text()
        if termino:
            self.usuarios = self.service.buscar_usuarios(termino)
        else:
            self.usuarios = self.service.listar_usuarios()
        self._poblar_tabla()

    def _get_selected_user_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self,
                "Seleccionar",
                "Seleccione un usuario de la tabla",
            )
            return None
        return int(self.table.item(row, 0).text())

    def _nuevo_usuario(self) -> None:
        dialog = UsuarioFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        nombre, username, password, rol_id = dialog.get_data()

        ok, msg = self.service.crear_usuario(
            nombre=nombre,
            username=username,
            password=password,
            rol_id=rol_id,
            audit_user_id=self._current_user.id,
        )

        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _editar_usuario(self) -> None:
        usuario_id = self._get_selected_user_id()
        if usuario_id is None:
            return

        # Find user in current data
        user_data = None
        for u in self.usuarios:
            if u["id"] == usuario_id:
                user_data = u
                break

        if not user_data:
            QMessageBox.warning(self, "Error", "Usuario no encontrado")
            return

        dialog = UsuarioFormDialog(self, user_data)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        nombre, _username, _password, rol_id = dialog.get_data()

        ok, msg = self.service.actualizar_usuario(
            usuario_id=usuario_id,
            nombre=nombre,
            rol_id=rol_id,
            audit_user_id=self._current_user.id,
        )

        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", "Usuario actualizado")
        else:
            QMessageBox.warning(self, "Error", msg)

    def _reset_password(self) -> None:
        usuario_id = self._get_selected_user_id()
        if usuario_id is None:
            return

        # Find username for dialog title
        username = ""
        for u in self.usuarios:
            if u["id"] == usuario_id:
                username = u["username"]
                break

        dialog = PasswordResetDialog(username, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        new_password = dialog.new_password or ""
        ok, msg = self.service.reset_password(
            usuario_id=usuario_id,
            new_password=new_password,
            audit_user_id=self._current_user.id,
        )

        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _desactivar_usuario(self) -> None:
        usuario_id = self._get_selected_user_id()
        if usuario_id is None:
            return

        # Find username
        username = ""
        for u in self.usuarios:
            if u["id"] == usuario_id:
                username = u["username"]
                break

        confirm = QMessageBox.question(
            self,
            "Confirmar desactivación",
            f"¿Está seguro de desactivar al usuario '{username}'?\n\n"
            "El usuario no podrá iniciar sesión.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.service.desactivar_usuario(
            usuario_id=usuario_id,
            audit_user_id=self._current_user.id,
        )

        if ok:
            self._cargar_datos()
            QMessageBox.information(self, "Éxito", msg)
        else:
            QMessageBox.warning(self, "Error", msg)

    def _reactivar_usuario(self) -> None:
        usuario_id = self._get_selected_user_id()
        if usuario_id is None:
            return

        # Find user data
        user_data = None
        for u in self.usuarios:
            if u["id"] == usuario_id:
                user_data = u
                break

        if not user_data:
            QMessageBox.warning(self, "Error", "Usuario no encontrado")
            return

        confirm = QMessageBox.question(
            self,
            "Confirmar reactivación",
            f"¿Está seguro de reactivar al usuario '{user_data['username']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, msg = self.service.actualizar_usuario(
            usuario_id=usuario_id,
            nombre=user_data["nombre"],
            rol_id=user_data["rol_id"],
            audit_user_id=self._current_user.id,
        )

        if ok:
            # Also reactivate the account (set activo=True). Solo se informa
            # éxito si el commit de reactivación realmente se completó.
            import logging

            from src.database.engine import SessionLocal
            from src.modules.usuarios.models.usuario_model import Usuario

            logger = logging.getLogger("delca.usuarios")
            session = SessionLocal()
            reactivado = False
            try:
                usuario = session.query(Usuario).filter(Usuario.id == usuario_id).first()
                if usuario:
                    usuario.activo = True
                    session.commit()
                    reactivado = True
                else:
                    logger.warning(
                        "Reactivación: usuario %s no encontrado en BD", usuario_id
                    )
            except Exception as e:
                session.rollback()
                logger.error("Error reactivando usuario %s: %s", usuario_id, e, exc_info=True)
            finally:
                session.close()

            if reactivado:
                self._cargar_datos()
                QMessageBox.information(self, "Éxito", "Usuario reactivado")
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "No se pudo reactivar el usuario. "
                    "La actualización se guardó pero la reactivación falló. "
                    "Consulte el log para más detalles.",
                )
        else:
            QMessageBox.warning(self, "Error", msg)
