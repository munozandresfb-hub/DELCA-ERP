"""Ticket printing service for thermal printers (network or local)."""

from __future__ import annotations

from PySide6.QtCore import QMarginsF, Qt
from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QTextDocument
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from src.modules.llantas.models.llanta_model import Llanta


class TiquetePrinter:
    """Generates and prints a ticket with tire and client information."""

    @staticmethod
    def print_tiquete(llanta: Llanta, parent_widget=None) -> tuple[bool, str]:
        """Print a ticket for the given tire.

        Works with any printer (network or local thermal printer).
        Returns (success, message).
        """
        if not llanta:
            return False, "No hay datos de llanta para imprimir"

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A7))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setPageMargins(QMarginsF(8, 8, 8, 8), QPageLayout.Unit.Millimeter)

        dialog = QPrintDialog(printer, parent_widget)
        dialog.setWindowTitle("Imprimir Tiquete")
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return False, "Impresión cancelada"

        html = TiquetePrinter._generar_html(llanta)

        doc = QTextDocument()
        doc.setHtml(html)
        doc.setPageSize(
            QPageSize(printer.pageLayout().pageSize()).size(QPageSize.Unit.Point)
        )

        painter = QPainter(printer)
        try:
            doc.drawContents(painter)
        finally:
            painter.end()

        return True, "Tiquete enviado a la impresora"

    @staticmethod
    def _generar_html(llanta: Llanta) -> str:
        """Generate HTML content for the ticket."""
        cliente_nombre = llanta.cliente.nombre if llanta.cliente else "—"
        cliente_nit = llanta.cliente.nit if llanta.cliente else "—"
        cliente_cel = llanta.cliente.celular if llanta.cliente else "—"

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    body {{
        font-family: 'Courier New', monospace;
        font-size: 10pt;
        margin: 0;
        padding: 4px;
    }}
    h2 {{
        text-align: center;
        font-size: 12pt;
        margin: 0 0 6px 0;
        border-bottom: 1px dashed #333;
        padding-bottom: 4px;
    }}
    .info {{
        width: 100%;
        border-collapse: collapse;
    }}
    .info td {{
        padding: 2px 4px;
        vertical-align: top;
    }}
    .info td.label {{
        font-weight: bold;
        white-space: nowrap;
        width: 35%;
    }}
    .info td.value {{
        font-weight: normal;
    }}
    .footer {{
        text-align: center;
        margin-top: 8px;
        padding-top: 4px;
        border-top: 1px dashed #333;
        font-size: 8pt;
    }}
</style>
</head>
<body>
<h2>TIQUETE — DELCA</h2>
<table class="info">
<tr><td class="label">Tiquete:</td><td class="value">{llanta.tiquete or "—"}</td></tr>
<tr><td class="label">Marca:</td><td class="value">{llanta.marca or "—"}</td></tr>
<tr><td class="label">Dimensión:</td><td class="value">{llanta.dimension or "—"}</td></tr>
<tr><td class="label">DOT:</td><td class="value">{llanta.dot or "—"}</td></tr>
<tr><td class="label">N° Orden:</td><td class="value">{llanta.numero_orden or "—"}</td></tr>
<tr><td class="label">Consecutivo:</td><td class="value">{llanta.consecutivo or "—"}</td></tr>
<tr><td class="label">Estado:</td><td class="value">{llanta.estado or "—"}</td></tr>
<tr><td class="label">Posición:</td><td class="value">{llanta.posicion or "—"}</td></tr>
<tr><td class="label">Diseño:</td><td class="value">{llanta.diseno_obj.nombre if hasattr(llanta, 'diseno_obj') and llanta.diseno_obj else "—"}</td></tr>
<tr><td class="label">Ancho/Perfil/Rin:</td><td class="value">{f'{llanta.ancho}/{llanta.perfil}R{llanta.rin}' if llanta.ancho and llanta.perfil and llanta.rin else "—"}</td></tr>
<tr><td class="label">Cliente:</td><td class="value">{cliente_nombre}</td></tr>
<tr><td class="label">NIT:</td><td class="value">{cliente_nit}</td></tr>
<tr><td class="label">Celular:</td><td class="value">{cliente_cel}</td></tr>
</table>
<div class="footer">— DELCA —</div>
</body>
</html>"""
