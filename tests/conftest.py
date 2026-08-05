"""Shared fixtures for DELCA ERP test suite."""

from collections.abc import Iterator
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.base import Base
from src.modules.usuarios.models.rol_model import Rol
from src.modules.usuarios.models.usuario_model import Usuario
from src.modules.usuarios.services.auth_service import AuthService


@pytest.fixture
def service_db(monkeypatch, tmp_path):
    """Bind get_session() services to a temp SQLite DB with full schema.

    Services (LlantaService, FacturaService, ReporteService, ...) obtain
    sessions via ``get_session()`` from ``src.database.engine``, which calls
    the module-level ``SessionLocal`` at call time. Monkeypatching that
    attribute redirects every service to an isolated, throwaway database.
    """
    import src.database.registry  # noqa: F401  — registers ALL models
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path / "service_test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)

    test_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine,
    )
    monkeypatch.setattr("src.database.engine.SessionLocal", test_session)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session() -> Iterator[Session]:
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    TestSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def admin_role(db_session: Session) -> Rol:
    """Create and return an ADMIN role."""
    role = Rol(nombre="ADMIN")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def operador_role(db_session: Session) -> Rol:
    """Create and return an OPERADOR role."""
    role = Rol(nombre="OPERADOR")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def test_user(db_session: Session, admin_role: Rol) -> Usuario:
    """Create and return a test admin user."""
    pw_hash = AuthService.hash_password("Test1234!")
    user = Usuario(
        nombre="Test User",
        username="testuser",
        password_hash=pw_hash,
        rol_id=admin_role.id,
        requires_password_change=False,
        password_changed_at=datetime.now(),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def locked_user(db_session: Session, admin_role: Rol) -> Usuario:
    """Create a user with a locked account."""
    pw_hash = AuthService.hash_password("Test1234!")
    user = Usuario(
        nombre="Locked User",
        username="locked",
        password_hash=pw_hash,
        rol_id=admin_role.id,
        failed_attempts=5,
        locked_until=datetime(2099, 1, 1),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
