from sqlalchemy.orm import Session, joinedload

from src.modules.clientes.models.cliente_model import Cliente
from src.modules.llantas.models.dimension_llanta_model import DimensionLlanta
from src.modules.llantas.models.llanta_model import Llanta


class LlantaRepository:
    """Repository for Llanta CRUD operations."""

    @staticmethod
    def get_all(session: Session) -> list[Llanta]:
        return session.query(Llanta).order_by(Llanta.id.desc()).all()

    @staticmethod
    def get_by_id(session: Session, llanta_id: int) -> Llanta | None:
        return session.query(Llanta).filter(Llanta.id == llanta_id).first()

    @staticmethod
    def get_by_tiquete(session: Session, tiquete: str) -> Llanta | None:
        return session.query(Llanta).filter(Llanta.tiquete == tiquete).first()

    @staticmethod
    def obtener_causa_rechazo(session: Session, causa_id: int):
        from src.modules.llantas.models.causa_rechazo_model import CausaRechazo

        return session.query(CausaRechazo).filter(CausaRechazo.id == causa_id).first()

    @staticmethod
    def search(
        session: Session,
        term: str = "",
        estado: str | None = None,
        cliente_id: int | None = None,
    ) -> list[Llanta]:
        query = session.query(Llanta)

        if term:
            pattern = f"%{term}%"
            query = query.outerjoin(Cliente, Llanta.cliente_id == Cliente.id).filter(
                Llanta.tiquete.ilike(pattern)
                | Llanta.marca.ilike(pattern)
                | Llanta.dimension.ilike(pattern)
                | Cliente.nombre.ilike(pattern)
                | Cliente.nit.ilike(pattern)
            )

        if estado:
            query = query.filter(Llanta.estado == estado)

        if cliente_id is not None:
            query = query.filter(Llanta.cliente_id == cliente_id)

        return query.order_by(Llanta.id.desc()).all()

    @staticmethod
    def count_by_estado(session: Session) -> dict[str, int]:
        from sqlalchemy import func

        results = (
            session.query(Llanta.estado, func.count(Llanta.id))
            .group_by(Llanta.estado)
            .all()
        )
        return {estado: count for estado, count in results}

    @staticmethod
    def create(session: Session, llanta: Llanta) -> Llanta:
        session.add(llanta)
        session.flush()
        return llanta

    # ── Catalog helpers ───────────────────────────────────────────────

    @staticmethod
    def get_all_marcas(session: Session) -> list:
        from src.modules.llantas.models.marca_llanta_model import MarcaLlanta

        return session.query(MarcaLlanta).order_by(MarcaLlanta.nombre).all()

    @staticmethod
    def get_all_dimensiones(session: Session) -> list:
        return session.query(DimensionLlanta).order_by(DimensionLlanta.ancho).all()
