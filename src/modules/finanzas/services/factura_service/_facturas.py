from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import joinedload

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.finanzas.models.factura_llanta_model import FacturaLlanta
from src.modules.llantas.models.llanta_model import Llanta


class _FacturasMixin:
    """Gestión de facturas: creación, consulta, listado y anulación."""

    @staticmethod
    def _generar_numero(session) -> str:
        """Generate next invoice number using timestamp (avoids race conditions).

        Microseconds are included so two invoices created within the same
        second still get distinct numbers (the ``numero`` column is UNIQUE).
        """
        now = datetime.now()
        return f"FAC-{now.strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def listar_facturas(
        estado: str | None = None,
        cliente_id: int | None = None,
    ) -> list[Factura]:
        with get_session() as session:
            q = session.query(Factura).options(
                joinedload(Factura.cliente),
                joinedload(Factura.llantas_detalle).joinedload(
                    FacturaLlanta.llanta
                ),
            )
            if estado:
                q = q.filter(Factura.estado == estado)
            if cliente_id:
                q = q.filter(Factura.cliente_id == cliente_id)
            facturas = q.order_by(Factura.fecha_emision.desc()).all()
            for f in facturas:
                session.expunge(f)
            return facturas

    @staticmethod
    def buscar(
        termino: str = "",
        cliente_id: int | None = None,
        estado: str | None = None,
        fecha_desde=None,
        fecha_hasta=None,
    ) -> list[Factura]:
        """Search invoices by term (client name/NIT/phone), client, estado, or date range."""
        with get_session() as session:
            q = session.query(Factura).options(
                joinedload(Factura.cliente),
                joinedload(Factura.llantas_detalle).joinedload(
                    FacturaLlanta.llanta
                ),
            )

            if termino:
                pattern = f"%{termino}%"
                q = q.outerjoin(Cliente, Factura.cliente_id == Cliente.id).filter(
                    Cliente.nombre.ilike(pattern)
                    | Cliente.nit.ilike(pattern)
                    | Cliente.celular.ilike(pattern)
                    | Cliente.telefono.ilike(pattern)
                )

            if cliente_id:
                q = q.filter(Factura.cliente_id == cliente_id)

            if estado:
                q = q.filter(Factura.estado == estado)

            if fecha_desde:
                q = q.filter(Factura.fecha_emision >= fecha_desde)
            if fecha_hasta:
                q = q.filter(Factura.fecha_emision <= fecha_hasta)

            facturas = q.order_by(Factura.fecha_emision.desc()).all()
            for f in facturas:
                session.expunge(f)
            return facturas

    @staticmethod
    def obtener_por_id(factura_id: int) -> Factura | None:
        with get_session() as session:
            factura = (
                session.query(Factura)
                .options(
                    joinedload(Factura.cliente),
                    joinedload(Factura.llantas_detalle).joinedload(
                        FacturaLlanta.llanta
                    ),
                )
                .filter(Factura.id == factura_id)
                .first()
            )
            if factura:
                session.expunge(factura)
            return factura

    @staticmethod
    def listar_llantas_facturables(cliente_id: int | None = None) -> list[Llanta]:
        """Tires not yet linked to any active (non-voided) invoice.

        Used by the invoice form to offer tires whose precio_venta pre-fills
        the line price. Tires already billed in a PENDIENTE/PARCIAL/PAGADA
        invoice are excluded so each tire is billed once.

        ``cliente_id`` filtra las llantas pendientes de facturación del
        cliente seleccionado (precarga en el formulario de factura).
        """
        with get_session() as session:
            facturadas = (
                session.query(FacturaLlanta.llanta_id)
                .join(Factura, FacturaLlanta.factura_id == Factura.id)
                .filter(Factura.estado != "ANULADA")
            )
            q = session.query(Llanta).filter(Llanta.id.notin_(facturadas))
            if cliente_id:
                q = q.filter(Llanta.cliente_id == cliente_id)
            llantas = q.order_by(Llanta.tiquete).all()
            for l in llantas:
                session.expunge(l)
            return llantas

    @staticmethod
    def crear(
        cliente_id: int,
        total: Decimal,
        observaciones: str | None = None,
        plazo_dias: int = 30,
        items: list[dict] | None = None,
    ) -> tuple[bool, str | Factura]:
        if not cliente_id:
            return False, "Debe seleccionar un cliente"
        if not total or total <= 0:
            return False, "El total debe ser mayor a cero"

        with get_session() as session:
            cliente = (
                session.query(Cliente)
                .filter(Cliente.id == cliente_id)
                .first()
            )
            if not cliente:
                return False, "Cliente no encontrado"

            # Validate tires exist before creating the invoice.
            # Items may be either: {"llanta_id": N, ...} (reencauchada) or
            # {"descripcion": "...", ...} (llanta nueva manual, sin llanta_id).
            items = items or []
            llanta_ids = [it.get("llanta_id") for it in items if it.get("llanta_id")]
            if len(llanta_ids) != len(set(llanta_ids)):
                return False, "La misma llanta no puede facturarse dos veces"
            for it in items:
                if not it.get("llanta_id") and not (it.get("descripcion") or "").strip():
                    return False, "Cada item debe tener una llanta o una descripción"
            llantas = (
                session.query(Llanta)
                .filter(Llanta.id.in_(llanta_ids))
                .all()
            ) if llanta_ids else []
            if len(llantas) != len(llanta_ids):
                return False, "Una o más llantas no existen"

            numero = _FacturasMixin._generar_numero(session)

            factura = Factura(
                cliente_id=cliente_id,
                numero=numero,
                fecha_emision=datetime.now(),
                total=total,
                saldo=total,
                estado="PENDIENTE",
                observaciones=observaciones.strip()
                if observaciones
                else None,
                plazo_dias=plazo_dias,
            )
            session.add(factura)
            session.flush()

            for it in items:
                session.add(
                    FacturaLlanta(
                        factura_id=factura.id,
                        llanta_id=it.get("llanta_id"),
                        descripcion=(
                            (it.get("descripcion") or "").strip() or None
                        ),
                        precio_unitario=Decimal(str(it.get("precio_unitario", 0))),
                    )
                )

            # Update client saldo
            cliente.saldo = (cliente.saldo or 0) + total
            session.expunge(factura)
            return True, factura

    @staticmethod
    def obtener_abonos_cliente(cliente_id: int) -> list[dict]:
        """Todos los abonos (pagos) de las facturas de un cliente.

        Para la ventana emergente de abonos del módulo Cartera (mismo
        formato que el detalle de abonos de Facturación, pero por cliente).
        """
        from src.modules.finanzas.models.pago_model import Pago

        with get_session() as session:
            filas = (
                session.query(Factura.numero, Pago)
                .join(Pago, Pago.factura_id == Factura.id)
                .filter(Factura.cliente_id == cliente_id)
                .order_by(Pago.fecha.desc())
                .all()
            )
            return [
                {
                    "factura_numero": num,
                    "fecha": p.fecha,
                    "metodo_pago": p.metodo_pago,
                    "referencia": p.referencia,
                    "valor": float(p.valor),
                }
                for num, p in filas
            ]

    @staticmethod
    def anular(factura_id: int) -> tuple[bool, str]:
        with get_session() as session:
            factura = (
                session.query(Factura)
                .filter(Factura.id == factura_id)
                .first()
            )
            if not factura:
                return False, "Factura no encontrada"
            if factura.estado == "ANULADA":
                return False, "La factura ya está anulada"
            if factura.estado == "PAGADA":
                return False, "No se puede anular una factura pagada"

            factura.estado = "ANULADA"

            # Revert client saldo
            cliente = (
                session.query(Cliente)
                .filter(Cliente.id == factura.cliente_id)
                .first()
            )
            if cliente:
                cliente.saldo = (cliente.saldo or 0) - factura.saldo

            return True, "Factura anulada"