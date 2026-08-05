"""Reportes de clientes — ReporteService para el dominio de clientes.

Contiene los reportes que consultan exclusivamente datos de clientes
(saldo, actividad, columnas por ciudad).
"""

from datetime import datetime

from sqlalchemy import func

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.llantas.models.llanta_model import Llanta


class _ClientesReports:
    """Reportes del dominio Clientes."""

    @staticmethod
    def clientes_por_ciudad() -> list[dict]:
        """Detailed client list with city, contact, tires-in-plant, and status."""
        with get_session() as session:
            sub_llantas = (
                session.query(
                    Llanta.cliente_id,
                    func.count(Llanta.id).label("cnt"),
                )
                .filter(
                    Llanta.estado.in_(["PENDIENTE", "APTA", "RECHAZADA", "REPARADA"]),
                )
                .group_by(Llanta.cliente_id)
                .subquery()
            )
            results = (
                session.query(
                    Cliente.nombre,
                    Cliente.ciudad,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.activo,
                    func.coalesce(sub_llantas.c.cnt, 0),
                )
                .outerjoin(sub_llantas, Cliente.id == sub_llantas.c.cliente_id)
                .order_by(Cliente.ciudad, Cliente.nombre)
                .all()
            )
            return [
                {
                    "nombre": r[0],
                    "ciudad": r[1] or "",
                    "contacto": r[2] or r[3] or "",
                    "nit": r[4] or "",
                    "activo": bool(r[5]),
                    "llantas_planta": r[6],
                }
                for r in results
            ]

    @staticmethod
    def clientes_activos_vs_inactivos(
        filtro: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Detailed client list with status and last-invoice date.

        Args:
            filtro: "ACTIVO", "INACTIVO", or None for all.
            fecha_desde: filter by last invoice ≥ this date.
            fecha_hasta: filter by last invoice ≤ this date.
        """
        with get_session() as session:
            from sqlalchemy import func as f

            q = session.query(
                Cliente.nombre,
                Cliente.telefono,
                Cliente.celular,
                Cliente.nit,
                Cliente.id,
                Cliente.activo,
                f.max(Factura.fecha_emision).label("ultima_vez"),
            ).outerjoin(Factura, Cliente.id == Factura.cliente_id)

            if filtro == "ACTIVO":
                q = q.filter(Cliente.activo.is_(True))
            elif filtro == "INACTIVO":
                q = q.filter(Cliente.activo.is_(False))

            results = (
                q.group_by(Cliente.id)
                .order_by(Cliente.nombre)
                .all()
            )
            return [
                {
                    "nombre": r[0],
                    "contacto": r[1] or r[2] or "",
                    "nit": r[3] or "",
                    "id": r[4],
                    "activo": bool(r[5]),
                    "ultima_vez": (
                        r[6].strftime("%Y-%m-%d") if r[6] else "—"
                    ),
                }
                for r in results
            ]

    @staticmethod
    def clientes_con_mayor_saldo(
        limite: int = 10,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clients with highest pending balance, with optional date filter."""
        from sqlalchemy import desc

        with get_session() as session:
            sub_fact = (
                session.query(
                    Factura.cliente_id,
                    Factura.fecha_emision,
                    func.row_number()
                    .over(
                        partition_by=Factura.cliente_id,
                        order_by=desc(Factura.fecha_emision),
                    )
                    .label("rn"),
                )
                .filter(Factura.saldo > 0)
                .subquery()
            )

            q = (
                session.query(
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.saldo,
                    sub_fact.c.fecha_emision,
                )
                .outerjoin(
                    sub_fact,
                    (Cliente.id == sub_fact.c.cliente_id) & (sub_fact.c.rn == 1),
                )
                .filter(Cliente.saldo > 0)
            )

            if fecha_desde:
                q = q.filter(
                    func.date(sub_fact.c.fecha_emision) >= func.date(fecha_desde),
                )
            if fecha_hasta:
                q = q.filter(
                    func.date(sub_fact.c.fecha_emision) <= func.date(fecha_hasta),
                )

            results = (
                q.order_by(Cliente.saldo.desc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "nombre": r[0],
                    "contacto": r[1] or r[2] or "",
                    "nit": r[3] or "",
                    "saldo": float(r[4] or 0),
                    "fecha_saldo": (
                        r[5].strftime("%Y-%m-%d") if r[5] else "—"
                    ),
                }
                for r in results
            ]

    @staticmethod
    def clientes_con_mayor_saldo_detalle(
        limite: int = 20,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clients with highest pending balance, with N° Cliente and date filter."""
        from sqlalchemy import desc

        with get_session() as session:
            sub_fact = (
                session.query(
                    Factura.cliente_id,
                    Factura.fecha_emision,
                    func.row_number()
                    .over(
                        partition_by=Factura.cliente_id,
                        order_by=desc(Factura.fecha_emision),
                    )
                    .label("rn"),
                )
                .filter(Factura.saldo > 0)
                .subquery()
            )

            q = (
                session.query(
                    Cliente.id,
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.saldo,
                    sub_fact.c.fecha_emision,
                )
                .outerjoin(
                    sub_fact,
                    (Cliente.id == sub_fact.c.cliente_id) & (sub_fact.c.rn == 1),
                )
                .filter(Cliente.saldo > 0)
            )

            if fecha_desde:
                q = q.filter(
                    func.date(sub_fact.c.fecha_emision) >= func.date(fecha_desde),
                )
            if fecha_hasta:
                q = q.filter(
                    func.date(sub_fact.c.fecha_emision) <= func.date(fecha_hasta),
                )

            results = (
                q.order_by(Cliente.saldo.desc())
                .limit(limite)
                .all()
            )
            return [
                {
                    "id": r[0],
                    "nombre": r[1],
                    "contacto": r[2] or r[3] or "",
                    "nit": r[4] or "",
                    "saldo": float(r[5] or 0),
                    "fecha_saldo": (
                        r[6].strftime("%Y-%m-%d") if r[6] else "—"
                    ),
                }
                for r in results
            ]