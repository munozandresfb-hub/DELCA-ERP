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


def sub_ultima_actividad(session):
    """Subquery: última fecha de MOVIMIENTO del cliente en la BD.

    Movimiento = cualquier evento con fecha registrada:
      - Ingreso de llantas (llantas.fecha_ingreso)
      - Cambios de estado (estados_llanta.fecha)
      - Cambios de ubicación / entregas (ubicaciones_llanta.fecha)
      - Facturación (facturas.fecha_emision)
    """
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

    union = (
        ingresos.union_all(estados)
        .union_all(ubicaciones)
        .union_all(facturas)
        .subquery()
    )
    return (
        session.query(
            union.c[0].label("cliente_id"),
            func.max(union.c[1]).label("ultima_actividad"),
        )
        .group_by(union.c[0])
        .subquery()
    )


def es_activo(llantas_planta: int, ultima_actividad, desde: datetime | None) -> bool:
    """Clasifica a un cliente según la definición operativa confirmada."""
    if llantas_planta > 0:
        return True
    if ultima_actividad is None:
        return False
    return desde is None or ultima_actividad >= desde


def contar_clientes_activos_inactivos(
    fecha_desde: datetime | None = None,
) -> tuple[int, int]:
    """Cuenta clientes ACTIVOS e INACTIVOS con la definición central.

    Args:
        fecha_desde: inicio del periodo de actividad. Si es None se usa
            "hace 1 año" (definición: ≥1 año sin movimientos = inactivo).

    Returns:
        (activos, inactivos).
    """
    if fecha_desde is None:
        now = datetime.now()
        fecha_desde = now.replace(year=now.year - 1)

    with get_session() as session:
        sub_planta = sub_llantas_en_planta(session)
        sub_actividad = sub_ultima_actividad(session)
        total = session.query(Cliente).count()
        activos = 0
        # Cliente.id en el SELECT ancla la entidad y evita que SQLAlchemy
        # duplique los subqueries (ambiguous column).
        for _, cnt, ult in (
            session.query(
                Cliente.id,
                func.coalesce(sub_planta.c.cnt, 0).label("cnt"),
                sub_actividad.c.ultima_actividad.label("ult"),
            )
            .outerjoin(sub_planta, Cliente.id == sub_planta.c.cliente_id)
            .outerjoin(sub_actividad, Cliente.id == sub_actividad.c.cliente_id)
            .all()
        ):
            if es_activo(cnt, ult, fecha_desde):
                activos += 1
        return activos, total - activos