"""Audit trail service — records all sensitive actions to the auditoria table."""

import json
import socket
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.database.engine import SessionLocal
from src.modules.auditoria.models.auditoria_model import Auditoria


def _hostname_or_ip() -> str | None:
    """Nombre del equipo o IP LAN del origen de la operación (forense)."""
    try:
        return socket.gethostname()
    except Exception:
        return None


def registrar_auditoria(
    usuario_id: int | None,
    entidad: str,
    accion: str,
    detalle: str | None = None,
    payload: dict[str, Any] | None = None,
    ip_origen: str | None = None,
    session: Session | None = None,
) -> Auditoria:
    """Record an audit event.

    Args:
        usuario_id: Who performed the action (None for system actions).
        entidad: Entity/table name (e.g. 'usuarios', 'facturas').
        accion: Action type — CREATE, UPDATE, DELETE, LOGIN, LOGOUT, FALLO_LOGIN.
        detalle: Human-readable description.
        payload: Optional JSON-serializable dict with change details.
        ip_origen: Optional origin (hostname/IP). If None, captures the local
            hostname automatically para trazabilidad forense multi-equipo.
        session: Optional DB session. If None, creates and commits a new one.

    Returns:
        The Auditoria ORM instance.
    """
    audit = Auditoria(
        usuario_id=usuario_id,
        entidad=entidad,
        accion=accion,
        detalle=detalle,
        payload_json=json.dumps(payload, default=str, ensure_ascii=False)
        if payload
        else None,
        ip_origen=ip_origen if ip_origen is not None else _hostname_or_ip(),
        fecha=datetime.now(),
    )

    if session:
        session.add(audit)
    else:
        own_session = SessionLocal()
        try:
            own_session.add(audit)
            own_session.commit()
        finally:
            own_session.close()

    return audit


def registrar_login(
    usuario_id: int, exitoso: bool, ip: str | None = None, session: Session | None = None
) -> Auditoria:
    """Record a login attempt."""
    return registrar_auditoria(
        usuario_id=usuario_id if exitoso else None,
        entidad="usuarios",
        accion="LOGIN" if exitoso else "FALLO_LOGIN",
        detalle=f"Inicio de sesión {'exitoso' if exitoso else 'fallido'}"
        if exitoso
        else None,
        session=session,
    )


def registrar_logout(usuario_id: int, session: Session | None = None) -> Auditoria:
    """Record a logout."""
    return registrar_auditoria(
        usuario_id=usuario_id,
        entidad="usuarios",
        accion="LOGOUT",
        detalle="Cierre de sesión",
        session=session,
    )


def registrar_cambio_password(
    usuario_id: int, session: Session | None = None
) -> Auditoria:
    """Record a password change."""
    return registrar_auditoria(
        usuario_id=usuario_id,
        entidad="usuarios",
        accion="UPDATE",
        detalle="Cambio de contraseña",
        session=session,
    )


def registrar_crud(
    usuario_id: int,
    entidad: str,
    accion: str,
    objeto_id: int | str | None = None,
    cambios: dict[str, Any] | None = None,
    session: Session | None = None,
) -> Auditoria:
    """Record a CRUD operation.

    Args:
        usuario_id: Who performed the action.
        entidad: Entity name.
        accion: CREATE, UPDATE, or DELETE.
        objeto_id: Primary key or identifier of the affected object.
        cambios: Dict of changed fields (old → new for UPDATE).
        session: Optional DB session. If None, creates and commits a new one.
    """
    detalle = f"{accion} en {entidad}"
    if objeto_id is not None:
        detalle += f" #{objeto_id}"

    return registrar_auditoria(
        usuario_id=usuario_id,
        entidad=entidad,
        accion=accion,
        detalle=detalle,
        payload=cambios,
        session=session,
    )
