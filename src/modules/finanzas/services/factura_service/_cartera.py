from collections import defaultdict
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from src.database.engine import get_session
from src.modules.clientes.models.cliente_model import Cliente
from src.modules.finanzas.models.factura_model import Factura
from src.modules.finanzas.models.pago_model import Pago


class _CarteraMixin:
    """Cartera de clientes: saldos pendientes, antigüedad y exportación."""

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
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        try:
            cartera = _CarteraMixin.obtener_cartera_clientes()
            aging = _CarteraMixin.obtener_antiguedad_saldos()

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