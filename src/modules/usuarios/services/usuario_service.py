"""Service layer for user management CRUD operations."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.database.engine import SessionLocal
from src.modules.usuarios.models.usuario_model import Usuario
from src.modules.usuarios.models.rol_model import Rol
from src.modules.usuarios.repositories.usuario_repository import UsuarioRepository
from src.modules.usuarios.services.auth_service import AuthService
from src.core.services.audit_service import registrar_crud


class UsuarioService:
    """Operations: list, create, update, deactivate, reset password, assign roles."""

    @staticmethod
    def listar_usuarios(session: Session | None = None) -> list[dict[str, Any]]:
        """Return all users with role name and status info."""
        close = False
        if session is None:
            session = SessionLocal()
            close = True
        try:
            usuarios = session.query(Usuario).order_by(Usuario.nombre).all()
            result = []
            for u in usuarios:
                result.append({
                    "id": u.id,
                    "nombre": u.nombre,
                    "username": u.username,
                    "rol_id": u.rol_id,
                    "rol_nombre": u.rol.nombre if u.rol else "Sin rol",
                    "ultimo_acceso": (
                        u.last_login.strftime("%Y-%m-%d %H:%M")
                        if u.last_login else "Nunca"
                    ),
                    "password_expired": AuthService.is_password_expired(u),
                    "bloqueado": (
                        u.locked_until is not None
                        and u.locked_until > datetime.now()
                    ),
                    "requires_password_change": u.requires_password_change,
                    "activo": bool(u.password_hash),
                })
            return result
        finally:
            if close:
                session.close()

    @staticmethod
    def get_roles(session: Session | None = None) -> list[dict[str, Any]]:
        """Return all available roles."""
        close = False
        if session is None:
            session = SessionLocal()
            close = True
        try:
            roles = session.query(Rol).order_by(Rol.nombre).all()
            return [{"id": r.id, "nombre": r.nombre} for r in roles]
        finally:
            if close:
                session.close()

    @staticmethod
    def crear_usuario(
        nombre: str,
        username: str,
        password: str,
        rol_id: int,
        session: Session | None = None,
        audit_user_id: int | None = None,
    ) -> tuple[bool, str]:
        """Create a new user with password hashing. Forces password change on first login."""
        valid, msg = AuthService.validate_password_strength(password)
        if not valid:
            return False, msg

        close = False
        if session is None:
            session = SessionLocal()
            close = True
        try:
            existing = UsuarioRepository.get_user_by_username(session, username)
            if existing:
                return False, f"El usuario '{username}' ya existe"

            password_hash = AuthService.hash_password(password)
            usuario = Usuario(
                nombre=nombre,
                username=username,
                password_hash=password_hash,
                rol_id=rol_id,
                requires_password_change=True,
            )
            session.add(usuario)
            session.flush()

            # Audit
            if audit_user_id:
                registrar_crud(
                    usuario_id=audit_user_id,
                    entidad="usuarios",
                    accion="CREATE",
                    objeto_id=usuario.id,
                    session=session,
                )

            if close:
                session.commit()
            return True, f"Usuario '{username}' creado exitosamente"
        except Exception as e:
            if close:
                session.rollback()
            return False, f"Error al crear usuario: {e}"
        finally:
            if close:
                session.close()

    @staticmethod
    def actualizar_usuario(
        usuario_id: int,
        nombre: str,
        rol_id: int,
        session: Session | None = None,
        audit_user_id: int | None = None,
    ) -> tuple[bool, str]:
        """Update user name and role."""
        close = False
        if session is None:
            session = SessionLocal()
            close = True
        try:
            usuario = session.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not usuario:
                return False, "Usuario no encontrado"

            old_nombre = usuario.nombre
            old_rol_id = usuario.rol_id
            usuario.nombre = nombre
            usuario.rol_id = rol_id

            if close:
                session.commit()

            if audit_user_id:
                registrar_crud(
                    usuario_id=audit_user_id,
                    entidad="usuarios",
                    accion="UPDATE",
                    objeto_id=usuario_id,
                    cambios={
                        "nombre": {"old": old_nombre, "new": nombre},
                        "rol_id": {"old": old_rol_id, "new": rol_id},
                    },
                    session=session,
                )

            if close:
                session.commit()
            return True, "Usuario actualizado exitosamente"
        except Exception as e:
            if close:
                session.rollback()
            return False, f"Error al actualizar usuario: {e}"
        finally:
            if close:
                session.close()

    @staticmethod
    def reset_password(
        usuario_id: int,
        new_password: str,
        session: Session | None = None,
        audit_user_id: int | None = None,
    ) -> tuple[bool, str]:
        """Reset a user's password and force change on next login."""
        valid, msg = AuthService.validate_password_strength(new_password)
        if not valid:
            return False, msg

        close = False
        if session is None:
            session = SessionLocal()
            close = True
        try:
            usuario = session.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not usuario:
                return False, "Usuario no encontrado"

            usuario.password_hash = AuthService.hash_password(new_password)
            usuario.password_changed_at = None
            usuario.requires_password_change = True
            usuario.failed_attempts = 0
            usuario.locked_until = None

            if close:
                session.commit()

            if audit_user_id:
                registrar_crud(
                    usuario_id=audit_user_id,
                    entidad="usuarios",
                    accion="UPDATE",
                    objeto_id=usuario_id,
                    cambios={"action": "password_reset"},
                    session=session,
                )

            if close:
                session.commit()
            return (
                True,
                "Contraseña reseteada exitosamente. "
                "El usuario deberá cambiarla al iniciar sesión.",
            )
        except Exception as e:
            if close:
                session.rollback()
            return False, f"Error al resetear contraseña: {e}"
        finally:
            if close:
                session.close()

    @staticmethod
    def desactivar_usuario(
        usuario_id: int,
        session: Session | None = None,
        audit_user_id: int | None = None,
    ) -> tuple[bool, str]:
        """Deactivate user by clearing password (cannot login).

        Note: Since Usuario doesn't have an 'activo' field, we clear the
        password hash to prevent login. Future migration should add an
        'activo' boolean column.
        """
        close = False
        if session is None:
            session = SessionLocal()
            close = True
        try:
            usuario = session.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not usuario:
                return False, "Usuario no encontrado"

            # Prevent self-deactivation
            if audit_user_id and usuario.id == audit_user_id:
                return False, "No puede desactivar su propio usuario"

            usuario.password_hash = ""
            usuario.requires_password_change = True
            usuario.failed_attempts = 0
            usuario.locked_until = None

            if close:
                session.commit()

            if audit_user_id:
                registrar_crud(
                    usuario_id=audit_user_id,
                    entidad="usuarios",
                    accion="DELETE",
                    objeto_id=usuario_id,
                    session=session,
                )

            if close:
                session.commit()
            return True, f"Usuario '{usuario.username}' desactivado exitosamente"
        except Exception as e:
            if close:
                session.rollback()
            return False, f"Error al desactivar usuario: {e}"
        finally:
            if close:
                session.close()

    @staticmethod
    def obtener_usuario(
        usuario_id: int,
        session: Session | None = None,
    ) -> dict[str, Any] | None:
        """Get a single user details."""
        close = False
        if session is None:
            session = SessionLocal()
            close = True
        try:
            u = session.query(Usuario).filter(Usuario.id == usuario_id).first()
            if not u:
                return None
            return {
                "id": u.id,
                "nombre": u.nombre,
                "username": u.username,
                "rol_id": u.rol_id,
                "rol_nombre": u.rol.nombre if u.rol else "Sin rol",
                "requires_password_change": u.requires_password_change,
                "ultimo_acceso": (
                    u.last_login.strftime("%Y-%m-%d %H:%M")
                    if u.last_login else "Nunca"
                ),
                "bloqueado": (
                    u.locked_until is not None
                    and u.locked_until > datetime.now()
                ),
            }
        finally:
            if close:
                session.close()

    @staticmethod
    def buscar_usuarios(
        termino: str,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        """Search users by name or username."""
        close = False
        if session is None:
            session = SessionLocal()
            close = True
        try:
            usuarios = (
                session.query(Usuario)
                .filter(
                    (Usuario.nombre.ilike(f"%{termino}%"))
                    | (Usuario.username.ilike(f"%{termino}%"))
                )
                .order_by(Usuario.nombre)
                .all()
            )
            result = []
            for u in usuarios:
                result.append({
                    "id": u.id,
                    "nombre": u.nombre,
                    "username": u.username,
                    "rol_id": u.rol_id,
                    "rol_nombre": u.rol.nombre if u.rol else "Sin rol",
                    "ultimo_acceso": (
                        u.last_login.strftime("%Y-%m-%d %H:%M")
                        if u.last_login else "Nunca"
                    ),
                    "password_expired": AuthService.is_password_expired(u),
                    "bloqueado": (
                        u.locked_until is not None
                        and u.locked_until > datetime.now()
                    ),
                    "requires_password_change": u.requires_password_change,
                })
            return result
        finally:
            if close:
                session.close()
