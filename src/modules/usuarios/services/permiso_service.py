"""Role-based permission checking service."""

import logging
from functools import lru_cache

from sqlalchemy.orm import Session

from src.config import settings
from src.database.engine import SessionLocal
from src.modules.usuarios.models.permiso_model import Permiso, rol_permiso
from src.modules.usuarios.models.rol_model import Rol, RolNombre

logger = logging.getLogger("delca.rbac")


# ── Permission codigos ─────────────────────────────────────────────────

class Perms:
    """Centralized permission code constants."""
    # Dashboard
    DASHBOARD_VER = "dashboard.ver"

    # Clientes
    CLIENTES_VER = "clientes.ver"
    CLIENTES_CREAR = "clientes.crear"
    CLIENTES_EDITAR = "clientes.editar"
    CLIENTES_ELIMINAR = "clientes.eliminar"

    # Llantas
    LLANTAS_VER = "llantas.ver"
    LLANTAS_CREAR = "llantas.crear"
    LLANTAS_EDITAR = "llantas.editar"
    LLANTAS_ELIMINAR = "llantas.eliminar"

    # Producción
    PRODUCCION_VER = "produccion.ver"
    PRODUCCION_GESTIONAR = "produccion.gestionar"

    # Planta
    PLANTA_VER = "planta.ver"
    PLANTA_GESTIONAR = "planta.gestionar"

    # Facturación
    FACTURACION_VER = "facturacion.ver"
    FACTURACION_CREAR = "facturacion.crear"
    FACTURACION_ANULAR = "facturacion.anular"

    # Cartera
    CARTERA_VER = "cartera.ver"
    CARTERA_COBRAR = "cartera.cobrar"

    # Inventario
    INVENTARIO_VER = "inventario.ver"
    INVENTARIO_AJUSTAR = "inventario.ajustar"

    # Kardex
    KARDEX_VER = "kardex.ver"

    # Reportes
    REPORTES_VER = "reportes.ver"

    # Automatización
    AUTOMATIZACION_VER = "automatizacion.ver"
    AUTOMATIZACION_GESTIONAR = "automatizacion.gestionar"

    # Backup
    BACKUP_GESTIONAR = "backup.gestionar"

    # Usuarios
    USUARIOS_GESTIONAR = "usuarios.gestionar"

    # Auditoría
    AUDITORIA_VER = "auditoria.ver"


@lru_cache(maxsize=1)
def _get_permiso_id_cache(session: Session) -> dict[str, int]:
    """Build a cache mapping codigo → permiso_id."""
    rows = session.query(Permiso.codigo, Permiso.id).all()
    return {row.codigo: row.id for row in rows}


def clear_permiso_cache() -> None:
    _get_permiso_id_cache.cache_clear()


def tiene_permiso(rol_id: int, permiso_codigo: str, session: Session | None = None) -> bool:
    """Check if a role has a specific permission.

    Caches the permiso→id mapping for performance.
    """
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        cache = _get_permiso_id_cache(session)
        permiso_id = cache.get(permiso_codigo)
        if permiso_id is None:
            return False

        result = (
            session.query(rol_permiso)
            .filter(
                rol_permiso.c.rol_id == rol_id,
                rol_permiso.c.permiso_id == permiso_id,
            )
            .first()
        )
        return result is not None
    finally:
        if close_session:
            session.close()


def tiene_permiso_por_usuario(user, permiso_codigo: str, session: Session | None = None) -> bool:
    """Convenience: pass a Usuario ORM object or any object with rol_id."""
    return tiene_permiso(user.rol_id, permiso_codigo, session)


def permisos_de_rol(rol_id: int, session: Session | None = None) -> list[str]:
    """Return all permission codigos for a given role."""
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True
    try:
        rows = (
            session.query(Permiso.codigo)
            .join(rol_permiso, Permiso.id == rol_permiso.c.permiso_id)
            .filter(rol_permiso.c.rol_id == rol_id)
            .all()
        )
        return [row.codigo for row in rows]
    finally:
        if close_session:
            session.close()


def require_permission(
    user, permiso_codigo: str, session: Session | None = None
) -> bool:
    """Middleware RBAC con soporte de shadow mode (expand-contract).

    - ADMIN (break-glass) siempre pasa.
    - Si settings.RBAC_ENFORCE=False (default, shadow mode): los denials se
      registran en el log con nivel INFO pero NO bloquean la acción — permite
      validar la matriz de permisos en producción sin interrumpir operación.
    - Si settings.RBAC_ENFORCE=True: los denials se registran con WARNING y
      bloquean la acción (retorna False).

    Uso en servicios/handlers sensibles:
        if not require_permission(usuario_actual, Perms.BACKUP_GESTIONAR):
            # denegado: mostrar mensaje o abortar
    """
    if user is None:
        return False

    # Break-glass: ADMIN pasa siempre (decisión de negocio D2).
    rol = getattr(user, "rol", None)
    rol_nombre = getattr(rol, "nombre", None)
    if rol_nombre == RolNombre.ADMIN.value:
        return True

    ok = tiene_permiso_por_usuario(user, permiso_codigo, session)
    if ok:
        return True

    username = getattr(user, "username", "?")
    if settings.RBAC_ENFORCE:
        logger.warning(
            "RBAC DENY: %s sin permiso %s (bloqueado)", username, permiso_codigo
        )
        return False
    logger.info(
        "RBAC SHADOW: %s sin permiso %s (no bloqueado)", username, permiso_codigo
    )
    return True
