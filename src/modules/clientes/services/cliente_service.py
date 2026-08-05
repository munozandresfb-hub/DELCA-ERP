from sqlalchemy import func

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.clientes.repositories.cliente_repository import ClienteRepository
from src.modules.llantas.models.llanta_model import Llanta


class ClienteService:
    """Business logic for client management."""

    @staticmethod
    def listar_clientes() -> list[Cliente]:
        with get_session() as session:
            clientes = ClienteRepository.get_all(session)
            for c in clientes:
                session.expunge(c)
            return clientes

    @staticmethod
    def buscar(termino: str) -> list[Cliente]:
        with get_session() as session:
            clientes = ClienteRepository.search(session, termino)
            for c in clientes:
                session.expunge(c)
            return clientes

    @staticmethod
    def obtener_por_id(cliente_id: int) -> Cliente | None:
        with get_session() as session:
            cliente = ClienteRepository.get_by_id(session, cliente_id)
            if cliente:
                session.expunge(cliente)
            return cliente

    @staticmethod
    def crear(
        nombre: str,
        nit: str,
        celular: str | None = None,
        email: str | None = None,
        direccion: str | None = None,
        ciudad: str | None = None,
    ) -> tuple[bool, str | Cliente]:
        if not nombre or not nombre.strip():
            return False, "El nombre es obligatorio"
        if not nit or not nit.strip():
            return False, "El NIT es obligatorio"

        with get_session() as session:
            existente = ClienteRepository.get_by_nit(session, nit)
            if existente:
                return False, f"Ya existe un cliente con NIT {nit}"

            cliente = Cliente(
                nombre=nombre.strip(),
                nit=nit.strip(),
                celular=celular.strip() if celular else None,
                email=email.strip() if email else None,
                direccion=direccion.strip() if direccion else None,
                ciudad=ciudad.strip() if ciudad else None,
            )
            cliente = ClienteRepository.create(session, cliente)
            session.expunge(cliente)
            return True, cliente

    @staticmethod
    def actualizar(
        cliente_id: int,
        nombre: str,
        nit: str,
        celular: str | None = None,
        email: str | None = None,
        direccion: str | None = None,
        ciudad: str | None = None,
        activo: bool = True,
        categoria_abc: str = "B",
    ) -> tuple[bool, str | Cliente]:
        with get_session() as session:
            cliente = ClienteRepository.get_by_id(session, cliente_id)
            if not cliente:
                return False, "Cliente no encontrado"

            # Check NIT uniqueness if changed
            if nit != cliente.nit:
                existente = ClienteRepository.get_by_nit(session, nit)
                if existente:
                    return False, f"Ya existe otro cliente con NIT {nit}"

            cliente.nombre = nombre.strip()
            cliente.nit = nit.strip()
            cliente.celular = celular.strip() if celular else None
            cliente.email = email.strip() if email else None
            cliente.direccion = direccion.strip() if direccion else None
            cliente.ciudad = ciudad.strip() if ciudad else None
            cliente.activo = activo
            cliente.categoria_abc = categoria_abc

            session.flush()
            session.expunge(cliente)
            return True, cliente

    @staticmethod
    def eliminar(cliente_id: int) -> tuple[bool, str]:
        with get_session() as session:
            if ClienteRepository.delete(session, cliente_id):
                return True, "Cliente eliminado"
            return False, "Cliente no encontrado"

    @staticmethod
    def obtener_ids_con_llantas_en_planta() -> set[int]:
        """Return set of client IDs that have tires in planta (not delivered)."""
        with get_session() as session:
            resultados = (
                session.query(Llanta.cliente_id)
                .filter(Llanta.estado.in_(["PENDIENTE", "APTA", "RECHAZADA", "REPARADA"]))
                .distinct()
                .all()
            )
            return {r[0] for r in resultados}

    @staticmethod
    def clasificacion_abc(clientes: list[Cliente]) -> dict[str, list[Cliente]]:
        """Classify clients by ABC category."""
        result: dict[str, list[Cliente]] = {"A": [], "B": [], "C": []}
        for c in clientes:
            cat = c.categoria_abc or "B"
            result[cat].append(c)
        return result
