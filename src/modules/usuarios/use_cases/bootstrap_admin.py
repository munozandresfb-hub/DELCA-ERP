"""Bootstrap the admin user, standard roles, and RBAC permissions.

Idempotent — safe to run on every application startup.
"""

from src.database.session import SessionLocal
from src.modules.usuarios.models.rol_model import Rol
from src.modules.usuarios.models.usuario_model import Usuario
from src.modules.usuarios.repositories.usuario_repository import UsuarioRepository
from src.modules.usuarios.services.auth_service import AuthService
from src.modules.usuarios.use_cases.bootstrap_rbac import bootstrap_rbac

# ── Standard roles ─────────────────────────────────────────────────────
STANDARD_ROLES = ["ADMIN", "GERENCIA", "OPERADOR"]


def _ensure_roles(session):
    """Create all standard roles if they don't exist."""
    roles = {}
    for role_name in STANDARD_ROLES:
        role = UsuarioRepository.get_rol_by_name(session, role_name)
        if not role:
            role = Rol(nombre=role_name)
            session.add(role)
            session.flush()
        roles[role_name] = role
    return roles


def _ensure_admin_user(session, admin_role: Rol):
    """Create the default admin user if no user exists."""
    admin_user = UsuarioRepository.get_user_by_username(session, "admin")
    if not admin_user:
        password_hash = AuthService.hash_password("admin123")
        admin_user = Usuario(
            nombre="Administrador Principal",
            username="admin",
            password_hash=password_hash,
            rol_id=admin_role.id,
            requires_password_change=True,
        )
        session.add(admin_user)
        session.flush()


def bootstrap_admin():
    """Run full bootstrap: roles → admin user → RBAC permissions."""
    session = SessionLocal()
    try:
        roles = _ensure_roles(session)
        _ensure_admin_user(session, roles["ADMIN"])
        session.commit()
    finally:
        session.close()

    # Seed RBAC permissions (separate session)
    bootstrap_rbac()
