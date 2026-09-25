"""Contexto del cliente para el agente WhatsApp.

Consulta la BD real de DELCA para dar al agente IA datos verídicos:
- Cliente por número de teléfono (normaliza formato).
- Saldo y estado de cuenta.
- Llantas en proceso (estados activos) y reencauchadas recientes.
- Últimas facturas/pagos.

SOLO LECTURA: el agente responde con datos reales pero nunca modifica la BD.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

# Registrar TODOS los modelos antes de usar mappers (app standalone/webhook)
import src.database.registry  # noqa: F401

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.llantas.models.llanta_model import Llanta
from src.modules.finanzas.models.factura_model import Factura

logger = logging.getLogger("delca.whatsapp")

# Normaliza "3001234567", "+57 300 123 4567", "573001234567" → "573001234567"
def normalizar_telefono(telefono: str) -> str:
    """Deja el teléfono en formato internacional sin símbolos (E.164 básico)."""
    digits = re.sub(r"\D", "", telefono)
    if digits.startswith("57"):
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return "57" + digits[1:]
    if len(digits) == 10 and digits.startswith("3"):
        return "57" + digits
    return digits


def _coincide_telefono(cliente: Cliente, telefono_norm: str) -> bool:
    """Compara un cliente con el teléfono normalizado (tolera formatos locales)."""
    for campo in (cliente.telefono, cliente.celular):
        if not campo:
            continue
        c_norm = normalizar_telefono(str(campo))
        if c_norm == telefono_norm:
            return True
        # Teléfono local sin 57 (ej. "3001234567" vs "573001234567")
        if telefono_norm.endswith(c_norm) or c_norm.endswith(telefono_norm):
            return True
    return False


def buscar_cliente_por_telefono(telefono: str) -> Cliente | None:
    """Busca el cliente cuyo teléfono/celular coincide con el número entrante."""
    telefono_norm = normalizar_telefono(telefono)
    if not telefono_norm:
        return None
    with get_session() as session:
        clientes = session.query(Cliente).limit(500).all()
        for c in clientes:
            if _coincide_telefono(c, telefono_norm):
                return c
    return None


def resumen_cliente(cliente: Cliente) -> dict[str, Any]:
    """Resumen legible para el prompt del agente (saldo, llantas activas)."""
    try:
        with get_session() as session:
            llantas = (
                session.query(Llanta)
                .filter(Llanta.cliente_id == cliente.id)
                .order_by(Llanta.fecha_ingreso.desc())
                .limit(10)
                .all()
            )
            facturas = (
                session.query(Factura)
                .filter(Factura.cliente_id == cliente.id)
                .order_by(Factura.id.desc())
                .limit(5)
                .all()
            )
    except Exception as e:
        logger.error("Error consultando contexto de cliente %s: %s", cliente.id, e)
        return {"error": "No se pudo consultar el contexto del cliente"}

    llantas_activas = [
        l for l in llantas if l.estado not in ("REENCAUCHADA", "RECHAZADA", "ENTREGADA")
    ]
    reencauchadas = [l for l in llantas if l.estado == "REENCAUCHADA"]

    saldo_total = sum(float(f.saldo or 0) for f in facturas)

    return {
        "nombre": cliente.nombre,
        "nit": cliente.nit,
        "telefono": cliente.telefono,
        "saldo_total": saldo_total,
        "llantas_en_proceso": [
            {
                "tiquete": l.tiquete,
                "estado": l.estado,
                "dimension": l.dimension,
                "marca": l.marca,
                "fecha_ingreso": str(l.fecha_ingreso),
            }
            for l in llantas_activas
        ],
        "llantas_reencauchadas_recientes": [
            {"tiquete": l.tiquete, "dimension": l.dimension}
            for l in reencauchadas[:5]
        ],
        "facturas_recientes": [
            {
                "id": f.id,
                "total": float(f.total or 0),
                "saldo": float(f.saldo or 0),
                "fecha": str(f.fecha_emision),
            }
            for f in facturas
        ],
    }


def resumen_por_telefono(telefono: str) -> dict[str, Any] | None:
    """Devuelve el resumen del cliente para el teléfono, o None si no se encuentra."""
    cliente = buscar_cliente_por_telefono(telefono)
    if not cliente:
        return None
    return resumen_cliente(cliente)