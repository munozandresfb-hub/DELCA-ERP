from datetime import datetime

from sqlalchemy import func

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.finanzas.models.pago_model import Pago  # noqa: F401 - needed for relationship resolution
from src.modules.llantas.models.estado_llanta_model import EstadoLlanta
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.llantas.models.ubicacion_llanta_model import UbicacionLlanta  # noqa: F401


def obtener_metricas() -> dict:
    """Get dashboard top-card metrics."""
    with get_session() as db:
        now = datetime.now()
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # --- Client metrics ---
        total_clientes = db.query(Cliente).count()
        clientes_activos = (
            db.query(Cliente).filter(Cliente.activo == True).count()
        )

        # --- Tire metrics ---
        # En planta = pendientes + aptas (recibidas o en proceso no retiradas)
        en_planta = (
            db.query(Llanta)
            .filter(Llanta.estado.in_(["PENDIENTE", "APTA"]))
            .count()
        )

        # En proceso = aptas (aceptadas por inspección inicial)
        en_produccion = (
            db.query(Llanta)
            .filter(Llanta.estado == "APTA")
            .count()
        )

        # Entregadas del mes = reencauchadas con último movimiento a CLIENTE en el mes
        ultimo_mov_cliente = (
            db.query(
                UbicacionLlanta.llanta_id,
                func.max(UbicacionLlanta.fecha).label("max_fecha"),
            )
            .filter(UbicacionLlanta.ubicacion == "CLIENTE")
            .group_by(UbicacionLlanta.llanta_id)
            .subquery()
        )
        entregadas_mes = (
            db.query(func.count(func.distinct(Llanta.id)))
            .join(
                ultimo_mov_cliente,
                Llanta.id == ultimo_mov_cliente.c.llanta_id,
            )
            .filter(
                Llanta.estado == "REENCAUCHADA",
                ultimo_mov_cliente.c.max_fecha >= inicio_mes,
            )
            .scalar()
        )

        # --- Financial metrics ---
        facturacion_mes = (
            db.query(func.coalesce(func.sum(Factura.total), 0))
            .filter(Factura.fecha_emision >= inicio_mes)
            .scalar()
        )

        cobrado_mes = (
            db.query(func.coalesce(func.sum(Factura.total), 0))
            .filter(
                Factura.fecha_emision >= inicio_mes,
                Factura.estado.in_(["PAGADA", "PARCIAL"]),
            )
            .scalar()
        )

        cartera_pendiente = (
            db.query(func.coalesce(func.sum(Factura.saldo), 0))
            .filter(Factura.saldo > 0)
            .scalar()
        )

    return {
        "clientes_activos": clientes_activos,
        "clientes_totales": total_clientes,
        "en_planta": en_planta,
        "en_produccion": en_produccion,
        "entregadas_mes": entregadas_mes,
        "facturacion_mes": float(facturacion_mes),
        "cobrado_mes": float(cobrado_mes),
        "cartera_pendiente": float(cartera_pendiente),
    }


def obtener_metricas_estados() -> dict:
    """Get per-state metrics: en_proceso, en_planta, rechazadas."""
    with get_session() as db:
        now = datetime.now()
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # En proceso = APTA (aceptada por inspección inicial)
        en_proceso = (
            db.query(Llanta)
            .filter(Llanta.estado == "APTA")
            .count()
        )

        # En planta (reencauchadas/reparadas/rechazadas no retiradas) = REENCAUCHADA + REPARADA + RECHAZADA
        en_planta = (
            db.query(Llanta)
            .filter(Llanta.estado.in_(["REENCAUCHADA", "REPARADA", "RECHAZADA"]))
            .count()
        )

        # Rechazadas en el mes
        rechazadas_mes = (
            db.query(func.count(func.distinct(EstadoLlanta.llanta_id)))
            .filter(
                EstadoLlanta.estado == "RECHAZADA",
                EstadoLlanta.fecha >= inicio_mes,
            )
            .scalar()
        )

        # Rechazadas total histórico no retiradas
        rechazadas_total = (
            db.query(Llanta)
            .filter(Llanta.estado == "RECHAZADA")
            .count()
        )

        return {
            "en_proceso": en_proceso,
            "en_planta": en_planta,
            "rechazadas_mes": rechazadas_mes,
            "rechazadas_total": rechazadas_total,
        }


def obtener_actividad_reciente(limite: int = 10) -> list[dict]:
    """Get recent state changes across all tires with code."""
    with get_session() as db:
        registros = (
            db.query(EstadoLlanta, Llanta.tiquete)
            .join(Llanta, EstadoLlanta.llanta_id == Llanta.id)
            .order_by(EstadoLlanta.fecha.desc())
            .limit(limite)
            .all()
        )
        return [
            {
                "llanta_id": r.EstadoLlanta.llanta_id,
                "tiquete": r.tiquete,
                "estado": r.EstadoLlanta.estado,
                "fecha": r.EstadoLlanta.fecha.strftime("%Y-%m-%d %H:%M")
                if r.EstadoLlanta.fecha
                else "",
            }
            for r in registros
        ]


def obtener_llantas_por_estado() -> list[dict]:
    """Get tire count grouped by state."""
    with get_session() as db:
        resultados = (
            db.query(Llanta.estado, func.count(Llanta.id))
            .group_by(Llanta.estado)
            .all()
        )
        return [
            {"estado": estado, "cantidad": cantidad}
            for estado, cantidad in resultados
        ]
