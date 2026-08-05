"""AuditService unit tests — audit trail recording."""

from datetime import datetime

import pytest

from src.core.services.audit_service import (
    registrar_auditoria,
    registrar_login,
    registrar_logout,
    registrar_crud,
)
from src.modules.auditoria.models.auditoria_model import Auditoria


class TestAuditService:
    """Audit event recording."""

    def test_registrar_auditoria(self, db_session):
        entry = registrar_auditoria(
            usuario_id=1,
            entidad="usuarios",
            accion="LOGIN",
            detalle="Test login",
            session=db_session,
        )
        db_session.flush()
        assert entry.id is not None
        assert entry.usuario_id == 1
        assert entry.entidad == "usuarios"
        assert entry.accion == "LOGIN"

    def test_registrar_auditoria_with_payload(self, db_session):
        entry = registrar_auditoria(
            usuario_id=1,
            entidad="facturas",
            accion="CREATE",
            detalle="Created invoice",
            payload={"total": 1500.00, "cliente": "Test Corp"},
            session=db_session,
        )
        db_session.flush()
        assert entry.payload_json is not None
        assert "total" in entry.payload_json

    def test_registrar_auditoria_no_user(self, db_session):
        entry = registrar_auditoria(
            usuario_id=None,
            entidad="sistema",
            accion="CREATE",
            detalle="System action",
            session=db_session,
        )
        db_session.flush()
        assert entry.usuario_id is None

    def test_registrar_login_exitoso(self, db_session):
        entry = registrar_login(usuario_id=1, exitoso=True)
        db_session.flush()
        assert entry.accion == "LOGIN"

    def test_registrar_login_fallido(self, db_session):
        entry = registrar_login(usuario_id=1, exitoso=False)
        db_session.flush()
        assert entry.accion == "FALLO_LOGIN"

    def test_registrar_logout(self, db_session):
        entry = registrar_logout(usuario_id=1)
        db_session.flush()
        assert entry.accion == "LOGOUT"

    def test_registrar_crud_create(self, db_session):
        entry = registrar_crud(
            usuario_id=1,
            entidad="clientes",
            accion="CREATE",
            objeto_id=42,
        )
        db_session.flush()
        assert entry.detalle is not None
        assert "CREATE" in entry.detalle
        assert "#42" in entry.detalle

    def test_registrar_crud_update_with_changes(self, db_session):
        changes = {
            "saldo": {"old": 1000, "new": 1500},
            "estado": {"old": "PENDIENTE", "new": "PAGADA"},
        }
        entry = registrar_crud(
            usuario_id=1,
            entidad="facturas",
            accion="UPDATE",
            objeto_id=7,
            cambios=changes,
        )
        db_session.flush()
        assert entry.payload_json is not None
        assert "saldo" in entry.payload_json
