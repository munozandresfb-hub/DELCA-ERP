from sqlalchemy.orm import Session

from src.modules.clientes.models.cliente_model import Cliente


class ClienteRepository:
    """Repository for Cliente CRUD operations."""

    @staticmethod
    def get_all(session: Session) -> list[Cliente]:
        return session.query(Cliente).order_by(Cliente.nombre).all()

    @staticmethod
    def get_by_id(session: Session, cliente_id: int) -> Cliente | None:
        return session.query(Cliente).filter(Cliente.id == cliente_id).first()

    @staticmethod
    def get_by_nit(session: Session, nit: str) -> Cliente | None:
        return session.query(Cliente).filter(Cliente.nit == nit).first()

    @staticmethod
    def search(session: Session, term: str) -> list[Cliente]:
        """Search clients by name, NIT, phone or email."""
        pattern = f"%{term}%"
        return (
            session.query(Cliente)
            .filter(
                Cliente.nombre.ilike(pattern)
                | Cliente.nit.ilike(pattern)
                | Cliente.telefono.ilike(pattern)
                | Cliente.celular.ilike(pattern)
                | Cliente.email.ilike(pattern)
            )
            .order_by(Cliente.nombre)
            .all()
        )

    @staticmethod
    def get_activos(session: Session) -> list[Cliente]:
        return (
            session.query(Cliente)
            .filter(Cliente.activo.is_(True))
            .order_by(Cliente.nombre)
            .all()
        )

    @staticmethod
    def create(session: Session, cliente: Cliente) -> Cliente:
        session.add(cliente)
        session.flush()
        return cliente

    @staticmethod
    def delete(session: Session, cliente_id: int) -> bool:
        cliente = session.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            return False
        session.delete(cliente)
        return True
