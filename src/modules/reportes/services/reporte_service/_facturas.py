"""Reportes de Finanzas (facturas)."""

from datetime import datetime

from sqlalchemy import func

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura


class _FacturasReports:
    """Reportes del dominio Facturación."""

    @staticmethod
    def facturas_detalle_por_mes(
        anio: int, mes: int | None = None,
    ) -> list[dict]:
        """Per-invoice detail for a given year/month."""
        with get_session() as session:
            q = session.query(
                Factura.id,
                Factura.numero,
                Factura.cliente_id,
                Cliente.nombre,
                Cliente.nit,
                Factura.total,
                Factura.saldo,
                Factura.estado,
                Factura.fecha_emision,
            ).join(Cliente, Factura.cliente_id == Cliente.id)

            if mes is not None:
                q = q.filter(
                    func.strftime("%Y-%m", Factura.fecha_emision) == f"{anio}-{mes:02d}"
                )
            else:
                q = q.filter(
                    func.strftime("%Y", Factura.fecha_emision) == str(anio)
                )

            facturas = q.order_by(Factura.fecha_emision.desc()).all()

            result = []
            for row in facturas:
                fid = row[0]
                num = row[1]
                result.append({
                    "id": int(fid or 0),
                    "cliente_id": int(row[2] or 0),
                    "cliente": row[3] or "—",
                    "nit": row[4] or "—",
                    "valor": float(row[5] or 0),
                    "saldo": float(row[6] or 0),
                    "estado": row[7] or "SIN ESTADO",
                    "fecha": row[8].strftime("%Y-%m-%d") if row[8] else "—",
                    "factura": f"#{num}" if num else f"ID {fid}",
                })
            return result

    @staticmethod
    def facturas_por_estado_detalle(estado: str | None = None) -> list[dict]:
        """Per-invoice list grouped by estado with cliente, total, fecha."""
        with get_session() as session:
            q = session.query(
                Factura.estado,
                Factura.id,
                Factura.cliente_id,
                Cliente.nombre,
                Cliente.nit,
                Factura.total,
                Factura.saldo,
                Factura.fecha_emision,
            ).join(Cliente, Factura.cliente_id == Cliente.id)
            if estado:
                q = q.filter(Factura.estado == estado)
            results = q.order_by(Factura.estado, Factura.fecha_emision.desc()).all()
            return [
                {
                    "id": int(r[1] or 0),
                    "cliente_id": int(r[2] or 0),
                    "cliente": r[3] or "—",
                    "nit": r[4] or "—",
                    "valor": float(r[5] or 0),
                    "saldo": float(r[6] or 0),
                    "fecha": r[7].strftime("%Y-%m-%d") if r[7] else "—",
                    "estado": r[0] or "SIN ESTADO",
                }
                for r in results
            ]