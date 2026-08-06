from datetime import datetime
from decimal import Decimal

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.finanzas.models.pago_model import Pago


class _PagosMixin:
    """Gestión de pagos y abonos a facturas."""

    @staticmethod
    def registrar_pago(
        factura_id: int,
        valor: Decimal,
        metodo_pago: str = "EFECTIVO",
        referencia: str | None = None,
    ) -> tuple[bool, str]:
        if valor <= 0:
            return False, "El valor del pago debe ser mayor a cero"

        with get_session() as session:
            factura = (
                session.query(Factura)
                .filter(Factura.id == factura_id)
                .first()
            )
            if not factura:
                return False, "Factura no encontrada"
            if factura.estado == "ANULADA":
                return False, "No se pueden registrar pagos en facturas anuladas"
            if factura.estado == "PAGADA":
                return False, "La factura ya está pagada"
            if valor > factura.saldo:
                restante = factura.saldo
                return (
                    False,
                    f"El pago ({valor}) supera el saldo pendiente ({restante})",
                )

            pago = Pago(
                factura_id=factura_id,
                valor=valor,
                metodo_pago=metodo_pago,
                referencia=referencia.strip() if referencia else None,
                fecha=datetime.now(),
            )
            session.add(pago)

            factura.saldo -= valor
            if factura.saldo == 0:
                factura.estado = "PAGADA"

            # Update client saldo
            cliente = (
                session.query(Cliente)
                .filter(Cliente.id == factura.cliente_id)
                .first()
            )
            if cliente:
                cliente.saldo = (cliente.saldo or 0) - valor

            return True, f"Pago registrado. Saldo restante: {factura.saldo}"

    @staticmethod
    def obtener_pagos(factura_id: int) -> list[Pago]:
        with get_session() as session:
            return (
                session.query(Pago)
                .filter(Pago.factura_id == factura_id)
                .order_by(Pago.fecha.desc())
                .all()
            )