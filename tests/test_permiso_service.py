"""PermisoService unit tests — RBAC permission checking."""

from src.database.engine import SessionLocal
from src.modules.usuarios.models.permiso_model import Permiso, rol_permiso
from src.modules.usuarios.models.rol_model import Rol
from src.modules.usuarios.services.permiso_service import (
    tiene_permiso,
    tiene_permiso_por_usuario,
    permisos_de_rol,
    clear_permiso_cache,
)


class TestPermisoService:
    """Permission checking with cached lookups."""

    def _seed(self, db_session):
        """Seed minimal permission data."""
        rol = Rol(nombre="TEST_ROLE")
        db_session.add(rol)
        db_session.flush()

        perm = Permiso(
            codigo="test.ver",
            nombre="Test View",
            modulo="test",
        )
        db_session.add(perm)
        db_session.flush()

        db_session.execute(
            rol_permiso.insert().values(rol_id=rol.id, permiso_id=perm.id)
        )
        db_session.commit()
        clear_permiso_cache()
        return rol, perm

    def test_tiene_permiso_true(self, db_session):
        rol, perm = self._seed(db_session)
        assert tiene_permiso(rol.id, "test.ver", db_session)

    def test_tiene_permiso_false(self, db_session):
        rol, perm = self._seed(db_session)
        assert not tiene_permiso(rol.id, "nonexistent.codigo", db_session)

    def test_tiene_permiso_different_role(self, db_session):
        rol, perm = self._seed(db_session)
        other = Rol(nombre="OTHER")
        db_session.add(other)
        db_session.flush()
        assert not tiene_permiso(other.id, "test.ver", db_session)

    def test_tiene_permiso_por_usuario(self, db_session, test_user, admin_role):
        """test_user has ADMIN role which should have permisos seeded properly."""
        # Seed permissions for admin_role
        perm = Permiso(
            codigo="dashboard.ver",
            nombre="Dashboard",
            modulo="dashboard",
        )
        db_session.add(perm)
        db_session.flush()
        db_session.execute(
            rol_permiso.insert().values(rol_id=admin_role.id, permiso_id=perm.id)
        )
        db_session.commit()
        clear_permiso_cache()
        assert tiene_permiso_por_usuario(test_user, "dashboard.ver", session=db_session)

    def test_permisos_de_rol(self, db_session):
        rol, perm = self._seed(db_session)
        codigos = permisos_de_rol(rol.id, session=db_session)
        assert "test.ver" in codigos

    def test_permisos_de_rol_empty_for_new_role(self, db_session):
        new_role = Rol(nombre="EMPTY")
        db_session.add(new_role)
        db_session.flush()
        assert permisos_de_rol(new_role.id, session=db_session) == []
