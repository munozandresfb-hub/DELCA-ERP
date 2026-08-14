from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QMessageBox,
    QDialog,
    QFormLayout,
    QDialogButtonBox,
)
from PySide6.QtCore import Qt

from src.modules.usuarios.viewmodels.login_viewmodel import LoginViewModel


class PasswordChangeDialog(QDialog):
    """Dialog to force the user to change an expired password."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cambiar Contraseña")
        self.setModal(True)
        self.resize(380, 220)
        self.new_password = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        msg = QLabel(
            "Su contraseña ha expirado o debe cambiarla por primera vez.\n"
            "La nueva contraseña debe cumplir los siguientes requisitos:\n"
            "• Mínimo 8 caracteres\n"
            "• Al menos una mayúscula\n"
            "• Al menos una minúscula\n"
            "• Al menos un número\n"
            "• Al menos un carácter especial"
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        form = QFormLayout()
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.Password)
        form.addRow("Nueva contraseña:", self.new_pass_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        form.addRow("Confirmar contraseña:", self.confirm_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def validate_and_accept(self):
        p1 = self.new_pass_input.text()
        p2 = self.confirm_input.text()

        if not p1:
            QMessageBox.warning(self, "Cambiar contraseña", "Ingrese la nueva contraseña")
            return
        if p1 != p2:
            QMessageBox.warning(self, "Cambiar contraseña", "Las contraseñas no coinciden")
            return

        from src.modules.usuarios.services.auth_service import AuthService
        valid, msg = AuthService.validate_password_strength(p1)
        if not valid:
            QMessageBox.warning(self, "Contraseña inválida", msg)
            return

        self.new_password = p1
        self.accept()


class LoginWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.viewmodel = LoginViewModel()
        self.main_window = None
        self._pending_user = None

        self.setWindowTitle("DELCA ERP Login")
        self.resize(400, 250)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        # Título
        title = QLabel("DELCA ERP")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Usuario
        username_label = QLabel("Usuario")
        layout.addWidget(username_label)

        self.username_input = QLineEdit()
        layout.addWidget(self.username_input)

        # Contraseña
        password_label = QLabel("Contraseña")
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # Botón Login
        login_button = QPushButton("Iniciar Sesión")
        login_button.clicked.connect(self.handle_login)
        layout.addWidget(login_button)

        self.setLayout(layout)

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()

        success, result = self.viewmodel.login(username, password)

        if not success:
            if isinstance(result, dict):
                error_msg = result.get("error", "Error de autenticación")
                locked = result.get("locked_until")
                if locked:
                    error_msg += f"\n(Bloqueo hasta: {locked})"
                QMessageBox.warning(self, "Login", error_msg)
            else:
                QMessageBox.warning(self, "Login", str(result))
            return

        # Login exitoso
        user = result["user"]
        needs_change = result.get("needs_password_change", False)

        if needs_change:
            self._pending_user = user
            self.prompt_password_change(user)
            return

        self.open_dashboard(user)

    def prompt_password_change(self, user):
        """Show password change dialog and handle the flow."""
        dialog = PasswordChangeDialog(self)
        if dialog.exec() != QDialog.Accepted or not dialog.new_password:
            QMessageBox.information(
                self, "Login",
                "Debe cambiar su contraseña para continuar. "
                "La sesión no se iniciará."
            )
            return

        ok, msg = self.viewmodel.change_password(user.id, dialog.new_password)
        if not ok:
            QMessageBox.warning(self, "Error", msg)
            return

        QMessageBox.information(
            self, "Contraseña actualizada",
            "Contraseña cambiada exitosamente."
        )
        self.open_dashboard(user)

    def open_dashboard(self, user):
        # Import lazy: MainWindow arrastra todas las vistas del sistema.
        # Cargarlo aquí evita ralentizar la aparición del login.
        from src.core.views.main_window import MainWindow

        self.main_window = MainWindow(user)
        self.main_window.show()
        self.close()
