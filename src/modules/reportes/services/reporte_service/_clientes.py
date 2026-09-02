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
from src.modules.llantas.services.llanta_service import ESTADOS_EN_PLANTA


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
                    Llanta.estado.in_(ESTADOS_EN_PLANTA),
                    (Llanta.ubicacion_actual.is_(None))
                    | (Llanta.ubicacion_actual != "CLIENTE"),
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
                    Cliente.email,
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
                    "email": r[4] or "",
                    "nit": r[5] or "",
                    "activo": bool(r[6]),
                    "llantas_planta": r[7],
                }
                for r in results
            ]

    @staticmethod
    def clientes_activos_vs_inactivos(
        filtro: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clientes con estado Activo/Inactivo (definición operativa confirmada).

        Definición:
          ACTIVO   = tiene ≥1 llanta en planta/producción (no entregada)
                     O ingresó llantas dentro del periodo [fecha_desde, fecha_hasta]
                     (movimiento reciente en la BD).
          INACTIVO = sin llantas en planta/producción Y su último ingreso de
                     llantas es anterior a fecha_desde (por defecto en la vista:
                     hace 12 meses → ≥1 año sin movimientos).

        Args:
            filtro: "ACTIVO", "INACTIVO", or None for all.
            fecha_desde: inicio de la ventana de actividad (ingresos de llantas).
            fecha_hasta: fin de la ventana de actividad.
        """
        with get_session() as session:
            # Llantas en planta/producción por cliente (no entregadas al cliente)
            sub_planta = (
                session.query(
                    Llanta.cliente_id,
                    func.count(Llanta.id).label("cnt"),
                )
                .filter(
                    Llanta.estado.in_(ESTADOS_EN_PLANTA),
                    (Llanta.ubicacion_actual.is_(None))
                    | (Llanta.ubicacion_actual != "CLIENTE"),
                )
                .group_by(Llanta.cliente_id)
                .subquery()
            )

            # Último ingreso de llanta por cliente (movimiento en la BD)
            sub_ingreso = (
                session.query(
                    Llanta.cliente_id,
                    func.max(Llanta.fecha_ingreso).label("ult_ingreso"),
                )
                .group_by(Llanta.cliente_id)
                .subquery()
            )

            results = (
                session.query(
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.id,
                    func.coalesce(sub_planta.c.cnt, 0),
                    sub_ingreso.c.ult_ingreso,
                )
                .outerjoin(sub_planta, Cliente.id == sub_planta.c.cliente_id)
                .outerjoin(sub_ingreso, Cliente.id == sub_ingreso.c.cliente_id)
                .order_by(Cliente.nombre)
                .all()
            )

            filas: list[dict] = []
            for r in results:
                llantas_planta = r[5] or 0
                ult_ingreso = r[6]
                # Movimiento reciente: ingresó llantas dentro del periodo
                mov_reciente = ult_ingreso is not None and (
                    fecha_desde is None or ult_ingreso >= fecha_desde
                )
                activo = (llantas_planta > 0) or mov_reciente
                if filtro == "ACTIVO" and not activo:
                    continue
                if filtro == "INACTIVO" and activo:
                    continue
                filas.append(
                    {
                        "nombre": r[0],
                        "contacto": r[1] or r[2] or "",
                        "nit": r[3] or "",
                        "id": r[4],
                        "activo": activo,
                        "ultima_vez": (
                            ult_ingreso.strftime("%Y-%m-%d") if ult_ingreso else "—"
                        ),
                        "llantas_planta": llantas_planta,
                    }
                )
            return filas

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
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.id,
                    Cliente.email,
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
                    "id": r[4],
                    "email": r[5] or "",
                    "saldo": float(r[6] or 0),
                    "fecha_saldo": (
                        r[7].strftime("%Y-%m-%d") if r[7] else "—"
                    ),
                }
                for r in results
            ]