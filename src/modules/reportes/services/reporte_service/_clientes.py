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
                .outerjoin(sub_actividad, Cliente.id == sub_actividad.c.cliente_id)
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
                    "activo": _es_activo(r[6], r[7], datetime.now()),
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
        """Clientes con estado Activo/Inactivo (definición operativa confirmada, opción B).

        Definición (evaluada con el fin del segmento [fecha_desde, fecha_hasta]):
          ACTIVO   = tiene ≥1 llanta en planta/producción (no entregada)
                     O tuvo actividad DESPUÉS del fin del segmento (última
                     actividad posterior a fecha_hasta — siguió trayendo).
          INACTIVO = sin llantas en planta/producción Y sin actividad posterior
                     al fin del segmento (última actividad ≤ fecha_hasta — dejó
                     de venir a más tardar al final del periodo) Y con historial
                     previo (alguna vez trajo llantas).

        Args:
            filtro: "ACTIVO", "INACTIVO", or None for all.
            fecha_desde: inicio del segmento de tiempo (delimita el periodo).
            fecha_hasta: fin del segmento — umbral de la actividad posterior.
        """
        with get_session() as session:
            sub_planta = _sub_llantas_en_planta(session)
            # Última actividad TOTAL (historial completo): la clasificación
            # evalúa si hubo actividad DESPUÉS del fin del segmento.
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
                activo = _es_activo(llantas_planta, ultima_actividad, fecha_hasta)
                if filtro == "ACTIVO" and not activo:
                    continue
                if filtro == "INACTIVO":
                    # INACTIVO = sin llantas en planta/producción + sin actividad
                    # posterior al fin del segmento (última actividad ≤ hasta) +
                    # con historial previo (los clientes sin ningún movimiento
                    # nunca trajeron llantas — no son recuperables).
                    if activo or ultima_actividad is None:
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
    def _sub_saldo_por_cliente(session, fecha_desde, fecha_hasta):
        """Subquery: saldo pendiente REAL por cliente (suma de facturas).

        El saldo se calcula desde las facturas (estado != ANULADA, saldo > 0)
        — NO del campo legacy Cliente.saldo — y las fechas filtran DENTRO del
        subquery (evita que un join vacío elimine todos los clientes).
        """
        q = (
            session.query(
                Factura.cliente_id,
                Factura.saldo,
                Factura.fecha_emision,
            )
            .filter(
                Factura.saldo > 0,
                Factura.estado != "ANULADA",
                Factura.cliente_id.isnot(None),
            )
        )
        if fecha_desde:
            q = q.filter(Factura.fecha_emision >= fecha_desde)
        if fecha_hasta:
            q = q.filter(Factura.fecha_emision <= fecha_hasta)
        fact_sub = q.subquery()
        return (
            session.query(
                fact_sub.c.cliente_id,
                func.sum(fact_sub.c.saldo).label("saldo"),
                func.max(fact_sub.c.fecha_emision).label("ultima_factura"),
            )
            .group_by(fact_sub.c.cliente_id)
            .subquery()
        )

    @staticmethod
    def clientes_con_mayor_saldo(
        limite: int = 10,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clientes con mayor saldo pendiente (calculado de facturas reales)."""
        with get_session() as session:
            sub_saldo = _ClientesReports._sub_saldo_por_cliente(
                session, fecha_desde, fecha_hasta
            )
            q = (
                session.query(
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    func.coalesce(sub_saldo.c.saldo, 0),
                    sub_saldo.c.ultima_factura,
                )
                .outerjoin(sub_saldo, Cliente.id == sub_saldo.c.cliente_id)
                .filter(func.coalesce(sub_saldo.c.saldo, 0) > 0)
                .order_by(func.coalesce(sub_saldo.c.saldo, 0).desc())
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
                for r in q
            ]

    @staticmethod
    def clientes_con_mayor_saldo_detalle(
        limite: int = 20,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict]:
        """Clientes con mayor saldo pendiente, con N° Cliente (facturas reales)."""
        with get_session() as session:
            sub_saldo = _ClientesReports._sub_saldo_por_cliente(
                session, fecha_desde, fecha_hasta
            )
            q = (
                session.query(
                    Cliente.nombre,
                    Cliente.telefono,
                    Cliente.celular,
                    Cliente.nit,
                    Cliente.id,
                    Cliente.email,
                    func.coalesce(sub_saldo.c.saldo, 0),
                    sub_saldo.c.ultima_factura,
                )
                .outerjoin(sub_saldo, Cliente.id == sub_saldo.c.cliente_id)
                .filter(func.coalesce(sub_saldo.c.saldo, 0) > 0)
                .order_by(func.coalesce(sub_saldo.c.saldo, 0).desc())
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
                for r in q
            ]