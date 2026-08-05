from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.finanzas.models.factura_llanta_model import FacturaLlanta
from src.modules.finanzas.models.pago_model import Pago
from src.modules.llantas.models.llanta_model import Llanta

class FacturaService:
    """Business logic for invoice (factura) management."""

    @staticmethod
    def _generar_numero(session) -> str:
        """Generate next invoice number using timestamp (avoids race conditions).

        Microseconds are included so two invoices created within the same
        second still get distinct numbers (the ``numero`` column is UNIQUE).
        """
        now = datetime.now()
        return f"FAC-{now.strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def listar_facturas(
        estado: str | None = None,
        cliente_id: int | None = None,
    ) -> list[Factura]:
        with get_session() as session:
            q = session.query(Factura).options(
                joinedload(Factura.cliente)
            )
            if estado:
                q = q.filter(Factura.estado == estado)
            if cliente_id:
                q = q.filter(Factura.cliente_id == cliente_id)
            facturas = q.order_by(Factura.fecha_emision.desc()).all()
            for f in facturas:
                session.expunge(f)
            return facturas

    @staticmethod
    def buscar(
        termino: str = "",
        cliente_id: int | None = None,
        estado: str | None = None,
        fecha_desde=None,
        fecha_hasta=None,
    ) -> list[Factura]:
        """Search invoices by term (client name/NIT/phone), client, estado, or date range."""
        with get_session() as session:
            q = session.query(Factura).options(
                joinedload(Factura.cliente)
            )

            if termino:
                pattern = f"%{termino}%"
                q = q.outerjoin(Cliente, Factura.cliente_id == Cliente.id).filter(
                    Cliente.nombre.ilike(pattern)
                    | Cliente.nit.ilike(pattern)
                    | Cliente.celular.ilike(pattern)
                    | Cliente.telefono.ilike(pattern)
                )

            if cliente_id:
                q = q.filter(Factura.cliente_id == cliente_id)

            if estado:
                q = q.filter(Factura.estado == estado)

            if fecha_desde:
                q = q.filter(Factura.fecha_emision >= fecha_desde)
            if fecha_hasta:
                q = q.filter(Factura.fecha_emision <= fecha_hasta)

            facturas = q.order_by(Factura.fecha_emision.desc()).all()
            for f in facturas:
                session.expunge(f)
            return facturas

    @staticmethod
    def obtener_por_id(factura_id: int) -> Factura | None:
        with get_session() as session:
            factura = (
                session.query(Factura)
                .options(
                    joinedload(Factura.cliente),
                    joinedload(Factura.llantas_detalle).joinedload(
                        FacturaLlanta.llanta
                    ),
                )
                .filter(Factura.id == factura_id)
                .first()
            )
            if factura:
                session.expunge(factura)
            return factura

    @staticmethod
    def listar_llantas_facturables() -> list[Llanta]:
        """Tires that are not yet linked to any active (non-voided) invoice.

        Used by the invoice form to offer tires whose precio_venta pre-fills
        the line price. Tires already billed in a PENDIENTE/PARCIAL/PAGADA
        invoice are excluded so each tire is billed once.
        """
        with get_session() as session:
            facturadas = (
                session.query(FacturaLlanta.llanta_id)
                .join(Factura, FacturaLlanta.factura_id == Factura.id)
                .filter(Factura.estado != "ANULADA")
            )
            llantas = (
                session.query(Llanta)
                .filter(Llanta.id.notin_(facturadas))
                .order_by(Llanta.tiquete)
                .all()
            )
            for l in llantas:
                session.expunge(l)
            return llantas

    @staticmethod
    def crear(
        cliente_id: int,
        total: Decimal,
        observaciones: str | None = None,
        plazo_dias: int = 30,
        items: list[dict] | None = None,
    ) -> tuple[bool, str | Factura]:
        if not cliente_id:
            return False, "Debe seleccionar un cliente"
        if not total or total <= 0:
            return False, "El total debe ser mayor a cero"

        with get_session() as session:
            cliente = (
                session.query(Cliente)
                .filter(Cliente.id == cliente_id)
                .first()
            )
            if not cliente:
                return False, "Cliente no encontrado"

            # Validate tires exist before creating the invoice
            items = items or []
            llanta_ids = [it.get("llanta_id") for it in items]
            llanta_ids = [i for i in llanta_ids if i is not None]
            if len(llanta_ids) != len(set(llanta_ids)):
                return False, "La misma llanta no puede facturarse dos veces"
            llantas = (
                session.query(Llanta)
                .filter(Llanta.id.in_(llanta_ids))
                .all()
            ) if llanta_ids else []
            if len(llantas) != len(llanta_ids):
                return False, "Una o más llantas no existen"

            numero = FacturaService._generar_numero(session)

            factura = Factura(
                cliente_id=cliente_id,
                numero=numero,
                fecha_emision=datetime.now(),
                total=total,
                saldo=total,
                estado="PENDIENTE",
                observaciones=observaciones.strip()
                if observaciones
                else None,
                plazo_dias=plazo_dias,
            )
            session.add(factura)
            session.flush()

            for it in items:
                session.add(
                    FacturaLlanta(
                        factura_id=factura.id,
                        llanta_id=it["llanta_id"],
                        precio_unitario=Decimal(str(it.get("precio_unitario", 0))),
                    )
                )

            # Update client saldo
            cliente.saldo = (cliente.saldo or 0) + total
            session.expunge(factura)
            return True, factura

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
    def anular(factura_id: int) -> tuple[bool, str]:
        with get_session() as session:
            factura = (
                session.query(Factura)
                .filter(Factura.id == factura_id)
                .first()
            )
            if not factura:
                return False, "Factura no encontrada"
            if factura.estado == "ANULADA":
                return False, "La factura ya está anulada"
            if factura.estado == "PAGADA":
                return False, "No se puede anular una factura pagada"

            factura.estado = "ANULADA"

            # Revert client saldo
            cliente = (
                session.query(Cliente)
                .filter(Cliente.id == factura.cliente_id)
                .first()
            )
            if cliente:
                cliente.saldo = (cliente.saldo or 0) - factura.saldo

            return True, "Factura anulada"

    @staticmethod
    def obtener_pagos(factura_id: int) -> list[Pago]:
        with get_session() as session:
            return (
                session.query(Pago)
                .filter(Pago.factura_id == factura_id)
                .order_by(Pago.fecha.desc())
                .all()
            )

    @staticmethod
    def obtener_cartera_clientes() -> list[dict]:
        """Get client balances with pending amounts, contact info, and payment history."""
        with get_session() as session:
            hoy = datetime.now()
            clientes = (
                session.query(Cliente)
                .filter(Cliente.activo.is_(True))
                .order_by(Cliente.nombre)
                .all()
            )
            cartera = []
            for c in clientes:
                total_pendiente = (
                    session.query(func.coalesce(func.sum(Factura.saldo), 0))
                    .filter(
                        Factura.cliente_id == c.id,
                        Factura.estado.in_(["PENDIENTE"]),
                    )
                    .scalar()
                )
                if total_pendiente > 0:
                    # Ultima fecha de factura
                    ultima_factura = (
                        session.query(func.max(Factura.fecha_emision))
                        .filter(
                            Factura.cliente_id == c.id,
                            Factura.estado.notin_(["ANULADA"]),
                        )
                        .scalar()
                    )
                    # Total abonado (suma de pagos en facturas de este cliente)
                    total_abonado = (
                        session.query(func.coalesce(func.sum(Pago.valor), 0))
                        .join(Factura, Pago.factura_id == Factura.id)
                        .filter(Factura.cliente_id == c.id)
                        .scalar()
                    )
                    dias_ultima = (hoy - ultima_factura).days if ultima_factura else 999
                    cartera.append(
                        {
                            "cliente_id": c.id,
                            "cliente_nombre": c.nombre,
                            "cliente_nit": c.nit,
                            "cliente_celular": c.celular or "",
                            "saldo_pendiente": float(total_pendiente),
                            "fecha_ultima_factura": (
                                ultima_factura.strftime("%Y-%m-%d")
                                if ultima_factura
                                else ""
                            ),
                            "total_abonado": float(total_abonado),
                            "dias_ultima_factura": dias_ultima,
                        }
                    )
            return cartera

    @staticmethod
    def obtener_antiguedad_saldos() -> list[dict]:
        """Get aging report for all pending invoices."""
        with get_session() as session:
            hoy = datetime.now()
            facturas = (
                session.query(Factura)
                .options(joinedload(Factura.cliente))
                .filter(
                    Factura.estado.in_(["PENDIENTE"]),
                    Factura.saldo > 0,
                )
                .order_by(Factura.fecha_emision.asc())
                .all()
            )
            result = []
            for f in facturas:
                dias = (hoy - f.fecha_emision).days
                cliente = f.cliente
                result.append(
                    {
                        "factura_id": f.id,
                        "numero": f.numero,
                        "cliente_nombre": cliente.nombre if cliente else "?",
                        "cliente_celular": cliente.celular if cliente else "",
                        "fecha": f.fecha_emision.strftime("%Y-%m-%d"),
                        "total": float(f.total),
                        "saldo": float(f.saldo),
                        "dias": dias,
                        "rango": (
                            "0-30"
                            if dias <= 30
                            else "31-60"
                            if dias <= 60
                            else "61-90"
                            if dias <= 90
                            else "90+"
                        ),
                    }
                )
            return result

    @staticmethod
    def exportar_cartera_excel(output_path: str) -> tuple[bool, str]:
        """Export cartera (aging + client balances) to a formatted Excel file.

        Creates two sheets:
          - Resumen Cartera:  client-level balances
          - Antigüedad Saldos: invoice-level aging detail
        Ready for automated collection calling.
        """
        try:
            import openpyxl
        except ImportError:
            return False, "openpyxl no instalado. Ejecute: pip install openpyxl"

        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, numbers
        from openpyxl.utils import get_column_letter

        try:
            cartera = FacturaService.obtener_cartera_clientes()
            aging = FacturaService.obtener_antiguedad_saldos()

            wb = Workbook()

            # ── Sheet 1: Resumen Cartera ─────────────────────────────
            ws1 = wb.active
            ws1.title = "Resumen Cartera"

            headers1 = ["Cliente", "Celular", "Ultima Factura", "Total Abonado", "Saldo Pendiente"]
            header_font = Font(bold=True, size=11)
            header_fill = PatternFill(start_color="2c3e50", end_color="2c3e50", fill_type="solid")
            header_font_white = Font(bold=True, size=11, color="FFFFFF")

            ws1.append(headers1)
            for col_idx, _ in enumerate(headers1, 1):
                cell = ws1.cell(row=1, column=col_idx)
                cell.font = header_font_white
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            for c in cartera:
                ws1.append([
                    c["cliente_nombre"],
                    c["cliente_celular"],
                    c["fecha_ultima_factura"],
                    c["total_abonado"],
                    c["saldo_pendiente"],
                ])

            # Column widths
            ws1.column_dimensions["A"].width = 35
            ws1.column_dimensions["B"].width = 16
            ws1.column_dimensions["C"].width = 16
            ws1.column_dimensions["D"].width = 16
            ws1.column_dimensions["E"].width = 18

            # Currency format for columns D and E
            for row_idx in range(2, len(cartera) + 2):
                for col_idx in [4, 5]:
                    cell = ws1.cell(row=row_idx, column=col_idx)
                    cell.number_format = '#,##0.00'

            # ── Sheet 2: Antigüedad de Saldos ────────────────────────
            ws2 = wb.create_sheet(title="Antigüedad Saldos")

            headers2 = [
                "Factura", "Cliente", "Celular", "Fecha Emision",
                "Total", "Saldo Pendiente", "Dias Mora", "Rango",
            ]
            ws2.append(headers2)
            for col_idx, _ in enumerate(headers2, 1):
                cell = ws2.cell(row=1, column=col_idx)
                cell.font = header_font_white
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            # Color fills by aging range
            fills = {
                "0-30":  PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
                "31-60": PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid"),
                "61-90": PatternFill(start_color="FCD5B4", end_color="FCD5B4", fill_type="solid"),
                "90+":   PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
            }
            font_colors = {
                "0-30":  Font(color="006100"),
                "31-60": Font(color="9C5700"),
                "61-90": Font(color="974706"),
                "90+":   Font(color="9C0006"),
            }

            for a in aging:
                row_data = [
                    a["numero"],
                    a["cliente_nombre"],
                    a["cliente_celular"],
                    a["fecha"],
                    a["total"],
                    a["saldo"],
                    a["dias"],
                    a["rango"],
                ]
                ws2.append(row_data)

                # Apply row coloring based on aging range
                current_row = ws2.max_row
                rango = a["rango"]
                fill = fills.get(rango)
                font = font_colors.get(rango)
                if fill:
                    for col_idx in range(1, len(headers2) + 1):
                        ws2.cell(row=current_row, column=col_idx).fill = fill
                if font:
                    for col_idx in range(1, len(headers2) + 1):
                        ws2.cell(row=current_row, column=col_idx).font = font

            # Column widths
            col_widths = [16, 30, 16, 14, 14, 16, 12, 14]
            for i, w in enumerate(col_widths, 1):
                ws2.column_dimensions[get_column_letter(i)].width = w

            # Currency format for total and saldo
            for row_idx in range(2, len(aging) + 2):
                for col_idx in [5, 6]:
                    cell = ws2.cell(row=row_idx, column=col_idx)
                    cell.number_format = '#,##0.00'

            # ── Sheet 3: Totales por rango (bonus) ───────────────────
            ws3 = wb.create_sheet(title="Totales por Rango")
            ws3.cell(row=1, column=1, value="Rango")
            ws3.cell(row=1, column=2, value="Total")
            ws3.cell(row=1, column=3, value="Facturas")
            ws3.cell(row=1, column=4, value="Acción Recomendada")
            for col_idx in range(1, 5):
                cell = ws3.cell(row=1, column=col_idx)
                cell.font = header_font_white
                cell.fill = header_fill

            from collections import defaultdict
            rangos = defaultdict(lambda: {"total": 0.0, "count": 0})
            for a in aging:
                rangos[a["rango"]]["total"] += a["saldo"]
                rangos[a["rango"]]["count"] += 1

            acciones = {
                "0-30":  "Recordatorio amistoso",
                "31-60": "Llamada de cobro preventivo",
                "61-90": "Cobro prioritario — escalar a gerencia",
                "90+":   "Cobro judicial — acción legal",
            }
            orden = ["0-30", "31-60", "61-90", "90+"]
            for i, r in enumerate(orden):
                d = rangos.get(r, {"total": 0.0, "count": 0})
                row_num = i + 2
                ws3.cell(row=row_num, column=1, value=r)
                ws3.cell(row=row_num, column=2, value=round(d["total"], 2))
                ws3.cell(row=row_num, column=2).number_format = '#,##0.00'
                ws3.cell(row=row_num, column=3, value=d["count"])
                ws3.cell(row=row_num, column=4, value=acciones.get(r, ""))
                # Color each row
                fill = fills.get(r)
                font = font_colors.get(r)
                if fill:
                    for col_idx in range(1, 5):
                        ws3.cell(row=row_num, column=col_idx).fill = fill
                if font:
                    for col_idx in range(1, 5):
                        ws3.cell(row=row_num, column=col_idx).font = font

            ws3.column_dimensions["A"].width = 14
            ws3.column_dimensions["B"].width = 14
            ws3.column_dimensions["C"].width = 12
            ws3.column_dimensions["D"].width = 38

            wb.save(output_path)
            return True, f"Cartera exportada: {len(cartera)} clientes, {len(aging)} facturas"

        except Exception as e:
            return False, f"Error exportando cartera: {e}"
