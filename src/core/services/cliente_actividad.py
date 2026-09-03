"""Definición central de "cliente activo/inactivo" (único punto de verdad).

Definición operativa CONFIRMADA por el usuario:
    ACTIVO   = tiene ≥1 llanta en planta/producción (no entregada)
               O tuvo CUALQUIER movimiento en la BD dentro del periodo
               (ingreso de llantas, cambios de estado, cambios de
               ubicación/entregas, facturación).
    INACTIVO = sin llantas en planta/producción Y sin movimientos en el
               periodo (por defecto: ≥1 año sin movimientos).

Este módulo se usa desde el Dashboard, el módulo de Reportes y cualquier
otra sección que necesite clasificar clientes — garantiza que TODAS las
vistas muestren el mismo número.
"""

from datetime import datetime

from sqlalchemy import func, union_all

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.llantas.models.estado_llanta_model import EstadoLlanta
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta
from src.modules.llantas.services.llanta_service import ESTADOS_EN_PLANTA


def sub_llantas_en_planta(session):
    """Subquery: cantidad de llantas en planta/producción por cliente (no entregadas)."""
    return (
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


def _union_movimientos(session, fecha_desde=None, fecha_hasta=None):
    """Unión de TODOS los movimientos del cliente (ingresos, estados,
    ubicaciones/entregas, facturas), opcionalmente filtrada por un segmento
    de tiempo [fecha_desde, fecha_hasta]."""
    ingresos = (
        session.query(
            Llanta.cliente_id.label("cliente_id"),
            Llanta.fecha_ingreso.label("fecha"),
        )
        .filter(Llanta.fecha_ingreso.isnot(None), Llanta.cliente_id.isnot(None))
    )
    estados = (
        session.query(
            Llanta.cliente_id.label("cliente_id"),
            EstadoLlanta.fecha.label("fecha"),
        )
        .join(EstadoLlanta, EstadoLlanta.llanta_id == Llanta.id)
        .filter(EstadoLlanta.fecha.isnot(None), Llanta.cliente_id.isnot(None))
    )
    ubicaciones = (
        session.query(
            Llanta.cliente_id.label("cliente_id"),
            UbicacionLlanta.fecha.label("fecha"),
        )
        .join(UbicacionLlanta, UbicacionLlanta.llanta_id == Llanta.id)
        .filter(UbicacionLlanta.fecha.isnot(None), Llanta.cliente_id.isnot(None))
    )
    facturas = (
        session.query(
            Factura.cliente_id.label("cliente_id"),
            Factura.fecha_emision.label("fecha"),
        )
        .filter(Factura.fecha_emision.isnot(None), Factura.cliente_id.isnot(None))
    )
    if fecha_desde:
        ingresos = ingresos.filter(Llanta.fecha_ingreso >= fecha_desde)
        estados = estados.filter(EstadoLlanta.fecha >= fecha_desde)
        ubicaciones = ubicaciones.filter(UbicacionLlanta.fecha >= fecha_desde)
        facturas = facturas.filter(Factura.fecha_emision >= fecha_desde)
    if fecha_hasta:
        ingresos = ingresos.filter(Llanta.fecha_ingreso <= fecha_hasta)
        estados = estados.filter(EstadoLlanta.fecha <= fecha_hasta)
        ubicaciones = ubicaciones.filter(UbicacionLlanta.fecha <= fecha_hasta)
        facturas = facturas.filter(Factura.fecha_emision <= fecha_hasta)

    return (
        ingresos.union_all(estados)
        .union_all(ubicaciones)
        .union_all(facturas)
        .subquery()
    )


def sub_movimientos_en_rango(session, fecha_desde=None, fecha_hasta=None):
    """Subquery: cantidad de movimientos del cliente DENTRO de [desde, hasta].

    Se usa para la clasificación: un cliente tuvo actividad en el segmento de
    tiempo si tiene ≥1 movimiento con fecha dentro del rango.
    """
    union = _union_movimientos(session, fecha_desde, fecha_hasta)
    return (
        session.query(
            union.c[0].label("cliente_id"),
            func.count(union.c[1]).label("movimientos"),
        )
        .group_by(union.c[0])
        .subquery()
    )


def sub_ultima_actividad(session):
    """Subquery: última fecha de MOVIMIENTO del cliente en la BD (historial completo).

    Movimiento = cualquier evento con fecha registrada:
      - Ingreso de llantas (llantas.fecha_ingreso)
      - Cambios de estado (estados_llanta.fecha)
      - Cambios de ubicación / entregas (ubicaciones_llanta.fecha)
      - Facturación (facturas.fecha_emision)
    """
    union = _union_movimientos(session)
    return (
        session.query(
            union.c[0].label("cliente_id"),
            func.max(union.c[1]).label("ultima_actividad"),
        )
        .group_by(union.c[0])
        .subquery()
    )


def es_activo(llantas_planta: int, movimientos_en_rango: int) -> bool:
    """Clasifica a un cliente según la definición operativa confirmada:

    ACTIVO = tiene ≥1 llanta en planta/producción (no entregada)
             O tuvo movimientos DENTRO del segmento de tiempo evaluado.
    INACTIVO = sin llantas en planta/producción Y sin movimientos en el segmento.
    """
    return llantas_planta > 0 or movimientos_en_rango > 0


def contar_clientes_activos_inactivos(
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
) -> tuple[int, int]:
    """Cuenta clientes ACTIVOS e INACTIVOS con la definición central.

    Args:
        fecha_desde / fecha_hasta: segmento de tiempo donde se evalúa la
            actividad. Por defecto: [hace 1 año, hoy] (definición: ≥1 año
            sin movimientos = inactivo).

    Returns:
        (activos, inactivos).
    """
    if fecha_desde is None:
        now = datetime.now()
        fecha_desde = now.replace(year=now.year - 1)
    if fecha_hasta is None:
        fecha_hasta = datetime.now()

    with get_session() as session:
        sub_planta = sub_llantas_en_planta(session)
        sub_mov = sub_movimientos_en_rango(session, fecha_desde, fecha_hasta)
        total = session.query(Cliente).count()
        activos = 0
        for _, cnt, mov in (
            session.query(
                Cliente.id,
                func.coalesce(sub_planta.c.cnt, 0).label("cnt"),
                func.coalesce(sub_mov.c.movimientos, 0).label("mov"),
            )
            .outerjoin(sub_planta, Cliente.id == sub_planta.c.cliente_id)
            .outerjoin(sub_mov, Cliente.id == sub_mov.c.cliente_id)
            .all()
        ):
            if es_activo(cnt, mov):
                activos += 1
        return activos, total - activos