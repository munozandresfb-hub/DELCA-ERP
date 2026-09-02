"""Reportes de clientes — ReporteService para el dominio de clientes.

Contiene los reportes que consultan exclusivamente datos de clientes
(saldo, actividad, columnas por ciudad).
"""

from datetime import datetime

from sqlalchemy import func

from src.core.services.cliente_actividad import (
    es_activo as _es_activo,
    sub_llantas_en_planta as _sub_llantas_en_planta,
    sub_ultima_actividad as _sub_ultima_actividad,
)
from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.llantas.models.llanta_model import Llanta


class _ClientesReports:
    """Reportes del dominio Clientes."""

    @staticmethod
    def clientes_por_ciudad() -> list[dict]:
        """Clientes por ciudad con llantas en planta y estado operativo.

        El estado (Activo/Inactivo) usa la definición dinámica confirmada
        (actividad en el último año o llantas en planta), NO el campo legacy.
        """
        desde = datetime.now().replace(
            year=datetime.now().year - 1, month=datetime.now().month,
            day=datetime.now().day,
        )
        with get_session() as session:
            sub_llantas = _sub_llantas_en_planta(session)
            sub_actividad = _sub_ultima_actividad(session)
            results = (
                session.query(
                    Cliente.nombre,
                    Cliente.ciudad,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.email,
                    Cliente.nit,
                    func.coalesce(sub_llantas.c.cnt, 0),
                    sub_actividad.c.ultima_actividad,
                )
                .outerjoin(sub_llantas, Cliente.id == sub_llantas.c.cliente_id)
                .outerjoin(
                    sub_actividad, Cliente.id == sub_actividad.c.cliente_id
                )
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
                    "activo": _es_activo(r[6], r[7], desde),
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
            sub_planta = _sub_llantas_en_planta(session)
            sub_actividad = _sub_ultima_actividad(session)

            results = (
                session.query(
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.id,
                    func.coalesce(sub_planta.c.cnt, 0),
                    sub_actividad.c.ultima_actividad,
                )
                .outerjoin(sub_planta, Cliente.id == sub_planta.c.cliente_id)
                .outerjoin(sub_actividad, Cliente.id == sub_actividad.c.cliente_id)
                .order_by(Cliente.nombre)
                .all()
            )

            filas: list[dict] = []
            for r in results:
                llantas_planta = r[5] or 0
                ultima_actividad = r[6]
                activo = _es_activo(llantas_planta, ultima_actividad, fecha_desde)
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
                            ultima_actividad.strftime("%Y-%m-%d")
                            if ultima_actividad
                            else "—"
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