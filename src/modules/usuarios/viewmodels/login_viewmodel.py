import logging

from src.modules.usuarios.use_cases.login_user import login_user

logger = logging.getLogger("delca.auth")


class LoginViewModel:

    def login(self, username: str, password: str):
        if not username:
            return False, {"error": "Ingrese usuario"}

        if not password:
            return False, {"error": "Ingrese contraseña"}

        result = login_user(username, password)

        if not result["success"]:
            return False, result

        return True, result

    def change_password(self, user_id: int, new_password: str) -> tuple[bool, str]:
        """Change the current user's password."""
        from src.modules.usuarios.services.auth_service import AuthService
        from src.database.session import SessionLocal
        from src.modules.usuarios.models.usuario_model import Usuario
        from src.core.services.audit_service import registrar_cambio_password

        session = SessionLocal()
        try:
            user = session.query(Usuario).filter_by(id=user_id).first()
            if not user:
                return False, "Usuario no encontrado"

            success, msg = AuthService.change_password(user, new_password, session)
            if success:
                session.commit()
                registrar_cambio_password(user_id)
            return success, msg
        except Exception as e:
            session.rollback()
            logger.error("Error cambiando contraseña: %s", e, exc_info=True)
            return False, "No se pudo cambiar la contraseña. Consulte el log."
        finally:
            session.close()
