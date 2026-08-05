from datetime import datetime

from sqlalchemy.orm import joinedload

from src.database.session import SessionLocal
from src.modules.usuarios.models.usuario_model import Usuario
from src.modules.usuarios.repositories.usuario_repository import UsuarioRepository
from src.modules.usuarios.services.auth_service import AuthService
from src.core.services.audit_service import registrar_login


def login_user(username: str, password: str) -> dict:
    """
    Authenticate a user.

    Returns a dict:
        {
            "success": bool,
            "user": Usuario | None,
            "error": str | None,
            "needs_password_change": bool,
            "is_expired": bool,
            "locked_until": str | None,
        }
    """
    session = SessionLocal()
    try:
        user = (
            session.query(Usuario)
            .options(joinedload(Usuario.rol))
            .filter(Usuario.username == username)
            .first()
        )

        if not user:
            return {
                "success": False,
                "user": None,
                "error": "Usuario o contraseña incorrectos",
                "needs_password_change": False,
                "is_expired": False,
                "locked_until": None,
            }

        # ── Audit: failed login for non-existent user ──────────────
        # (user exists from here on, checks happen below)

        # ── Check account lock ─────────────────────────────────────
        if AuthService.is_account_locked(user):
            remaining = (
                user.locked_until - datetime.now()
            ).seconds // 60 if user.locked_until else 15
            return {
                "success": False,
                "user": None,
                "error": f"Cuenta bloqueada. Intente de nuevo en {remaining} minutos",
                "needs_password_change": False,
                "is_expired": False,
                "locked_until": user.locked_until.strftime("%Y-%m-%d %H:%M")
                if user.locked_until else None,
            }

        # ── Verify password ────────────────────────────────────────
        password_ok = AuthService.verify_password(password, user.password_hash)

        if not password_ok:
            locked = AuthService.record_failed_attempt(user, session)
            session.commit()

            # Audit the failed attempt
            registrar_login(usuario_id=user.id, exitoso=False)

            if locked:
                return {
                    "success": False,
                    "user": None,
                    "error": "Cuenta bloqueada por 15 minutos (5 intentos fallidos)",
                    "needs_password_change": False,
                    "is_expired": False,
                    "locked_until": user.locked_until.strftime("%Y-%m-%d %H:%M")
                    if user.locked_until else None,
                }
            return {
                "success": False,
                "user": None,
                "error": "Usuario o contraseña incorrectos",
                "needs_password_change": False,
                "is_expired": False,
                "locked_until": None,
            }

        # ── Successful login ───────────────────────────────────────
        # Reset failed attempts
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = datetime.now()
        session.commit()
        session.expunge(user)  # Detach so lazy loads work after session.close()

        # Audit the successful login
        registrar_login(usuario_id=user.id, exitoso=True)

        # Check password status
        needs_change = bool(user.requires_password_change)
        is_expired = AuthService.is_password_expired(user)

        return {
            "success": True,
            "user": user,
            "error": None,
            "needs_password_change": needs_change or is_expired,
            "is_expired": is_expired,
            "locked_until": None,
        }

    except Exception as e:
        session.rollback()
        return {
            "success": False,
            "user": None,
            "error": f"Error de autenticación: {e}",
            "needs_password_change": False,
            "is_expired": False,
            "locked_until": None,
        }
    finally:
        session.close()
