"""Impresión del tiquete: Hoja de Proceso de Reencauche DELCA (formato aprobado).

La hoja FÍSICA es VERTICAL: 103 x 279 mm (medida por el usuario). El PDF
escaneado quedó apaisado (misma relación de aspecto, 2.71:1) — el fondo se
pre-renderizó ROTADO a vertical (assets/hoja_proceso_reencauche_v.png).

El formato (inmodificable, aprobado por acreditación) se imprime como FONDO y
los datos de la llanta se superponen (overlay) en las cajas de la parte
superior de la hoja, con texto HORIZONTAL como el llenado manual real:

  Talón (bloque 1, parte superior): Cliente + Tiquete, Dimensión, Diseño,
                                    O.S., Serie(DOT)
  Cuerpo (bloque 2, debajo del talón): Cliente + Tiquete, Dimensión,
                                       Diseño, Serie(DOT), O.S.

Posiciones en % según el impreso de referencia (foto del formato llenado).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSizeF, Qt
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPainter, QPixmap
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from src.modules.llantas.models.llanta_model import Llanta

# ── Hoja física (mm) — vertical, medida por el usuario ─────────────────
PAGINA_MM = (103.0, 279.0)

# Base de recursos: _MEIPASS en el EXE onefile, raíz del proyecto en fuente
_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[4]))

FONDO = _BASE / "assets" / "hoja_proceso_reencauche_v.png"


def _mm(x_pct: float, y_pct: float, w_pct: float, h_pct: float) -> QRectF:
    """Convierte porcentajes de la hoja (0-100) a un QRectF en milímetros."""
    pw, ph = PAGINA_MM
    return QRectF(x_pct / 100 * pw, y_pct / 100 * ph,
                  w_pct / 100 * pw, h_pct / 100 * ph)


# ── Posiciones de los campos (rectángulos en mm, texto horizontal) ─────
# Datos: % de la hoja según el impreso de referencia llenado.
CAMPOS: dict[str, tuple[QRectF, str]] = {
    # Talón (bloque 1) — parte superior
    "talon_cliente":   (_mm(3.0, 4.0, 42.0, 6.0), "cliente"),
    "talon_tiquete":   (_mm(8.0, 10.0, 28.0, 3.5), "tiquete"),
    "talon_dimension": (_mm(38.0, 10.0, 24.0, 3.5), "dimension"),
    "talon_diseno":    (_mm(64.0, 10.0, 28.0, 3.5), "diseno"),
    "talon_os":        (_mm(8.0, 14.0, 28.0, 3.5), "os"),
    "talon_serie":     (_mm(38.0, 14.0, 24.0, 3.5), "serie"),
    # Cuerpo (bloque 2) — debajo del talón
    "cuerpo_cliente":  (_mm(3.0, 19.5, 42.0, 5.0), "cliente"),
    "cuerpo_tiquete":  (_mm(8.0, 23.5, 24.0, 3.5), "tiquete"),
    "cuerpo_dimension": (_mm(34.0, 23.5, 24.0, 3.5), "dimension"),
    "cuerpo_diseno":   (_mm(8.0, 27.5, 24.0, 3.5), "diseno"),
    "cuerpo_serie":    (_mm(34.0, 27.5, 24.0, 3.5), "serie"),
    "cuerpo_os":       (_mm(8.0, 31.5, 24.0, 3.5), "os"),
}


class TiquetePrinter:
    """Imprime la hoja de proceso con los datos de la llanta superpuestos."""

    @staticmethod
    def print_tiquete(llanta: Llanta, parent_widget=None) -> tuple[bool, str]:
        """Imprime la hoja de proceso de reencauche con los datos de la llanta.

        Muestra el diálogo de impresión (el usuario elige impresora) y envía
        la hoja con el formato aprobado + datos en las cajas correspondientes.
        Devuelve (success, message).
        """
        if not llanta:
            return False, "No hay datos de llanta para imprimir"

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QSizeF(*PAGINA_MM), QPageSize.Unit.Millimeter))
        printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)

        dialog = QPrintDialog(printer, parent_widget)
        dialog.setWindowTitle("Imprimir Hoja de Proceso")
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return False, "Impresión cancelada"

        datos = TiquetePrinter._datos_llanta(llanta)

        painter = QPainter(printer)
        try:
            # Trabajar en milímetros: escala = dpi / 25.4
            res = printer.resolution()
            painter.scale(res / 25.4, res / 25.4)

            TiquetePrinter._dibujar_fondo(painter)
            TiquetePrinter._dibujar_datos(painter, datos)
        finally:
            painter.end()

        return True, "Hoja de proceso enviada a la impresora"

    # ── Fondo (formato aprobado) ───────────────────────────────────────

    @staticmethod
    def _dibujar_fondo(painter: QPainter) -> None:
        """Dibuja la hoja escaneada como fondo (escala al tamaño físico)."""
        if not FONDO.exists():
            painter.fillRect(QRectF(0, 0, *PAGINA_MM), Qt.white)
            painter.drawRect(QRectF(0, 0, *PAGINA_MM))
            return

        pix = QPixmap(str(FONDO))
        if pix.isNull():
            painter.fillRect(QRectF(0, 0, *PAGINA_MM), Qt.white)
            return
        painter.drawPixmap(QRectF(0, 0, *PAGINA_MM), pix, QRectF(pix.rect()))

    # ── Datos de la llanta ─────────────────────────────────────────────

    @staticmethod
    def _datos_llanta(llanta: Llanta) -> dict[str, str]:
        """Extrae los valores a imprimir. serie = DOT (confirmado por el usuario)."""
        cliente = llanta.cliente.nombre if llanta.cliente else "—"
        diseno = (
            llanta.diseno_obj.nombre
            if hasattr(llanta, "diseno_obj") and llanta.diseno_obj
            else "—"
        )
        return {
            "cliente": cliente,
            # El tiquete se imprime SIN el prefijo "J" de la serie (ej. J24537 → 24537)
            "tiquete": (llanta.tiquete or "—").removeprefix("J"),
            "dimension": llanta.dimension or "—",
            "diseno": diseno,
            "os": llanta.numero_orden or "—",
            "serie": llanta.dot or "—",
        }

    # ── Overlay de datos ───────────────────────────────────────────────

    @staticmethod
    def _dibujar_datos(painter: QPainter, datos: dict[str, str]) -> None:
        """Escribe cada dato en su caja (texto horizontal, como el llenado real)."""
        for campo, (rect, clave) in CAMPOS.items():
            valor = datos.get(clave, "")
            if not valor or valor == "—":
                continue
            fuente = TiquetePrinter._fuente_para(painter, valor, rect)
            painter.setFont(fuente)
            painter.setPen(Qt.black)
            # Texto horizontal centrado verticalmente, alineado a la izquierda
            painter.drawText(rect.adjusted(1, 0, -1, 0),
                             Qt.AlignLeft | Qt.AlignVCenter, valor)

    @staticmethod
    def _fuente_para(painter: QPainter, texto: str, rect: QRectF) -> QFont:
        """Elige un tamaño de fuente que quepa en la caja (en mm)."""
        for size in (10, 9, 8, 7, 6, 5):
            font = QFont("Arial", size)
            font.setBold(True)
            painter.setFont(font)
            fm = painter.fontMetrics()
            if fm.horizontalAdvance(texto) <= rect.width() * 0.95:
                return font
        return QFont("Arial", 5)