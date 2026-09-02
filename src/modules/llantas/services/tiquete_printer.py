"""Impresión del tiquete: Hoja de Proceso de Reencauche DELCA (formato aprobado).

OBJETIVO: imprimir SOLO los datos (cliente + llanta) sobre la hoja de proceso
que YA viene pre-impresa con el formato aprobado/acreditado. NO se imprime el
formulario en blanco ni la hoja en blanco: el fondo es la hoja física.

ESTRATEGIA DE IMPRESIÓN (verificada contra los drivers instalados):

La hoja FÍSICA es VERTICAL: 103 x 279 mm, alimentada en la bandeja. NINGÚN
driver instalado soporta un tamaño de papel personalizado de 103x279 mm
(EPSON L380: solo Carta/A4; HP Ink Tank: 27 tamaños fijos sin 103x279).
Forzar ese tamaño hace que Windows rechace el trabajo al cargarlo.

Por eso se imprime en el tamaño del driver (Carta, que ambas impresoras
soportan y cuya altura 279.4 mm coincide con la hoja física) y los DATOS se
dibujan en la ZONA IZQUIERDA del área imprimible (0-103 mm de ancho), como
hacía el programa anterior: la franja izquierda de la impresión cae sobre la
hoja pre-impresa (el resto de la página no se pinta, sin gastar tinta).

Resolución 300 DPI: raster ligero para el driver.

Calibración en data/impresion_config.json:
- zona_x_mm / zona_y_mm: desplazamiento GLOBAL (mm) de todos los datos.
- campos: {campo: {"dx": mm, "dy": mm}} — ajuste fino por campo.

Se dibuja en píxeles de dispositivo (sin painter.scale): las fuentes en
puntos conservan su tamaño físico real y el ajuste de fuente compara
píxeles contra píxeles.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPainter, QPen, QPixmap
from PySide6.QtPrintSupport import (
    QPrintDialog,
    QPrintPreviewDialog,
    QPrinter,
    QPrinterInfo,
)

from src.config import settings
from src.modules.llantas.models.llanta_model import Llanta

# ── Hoja física (mm) — vertical, medida por el usuario ─────────────────
PAGINA_MM = (103.0, 279.0)

# Base de recursos: _MEIPASS en el EXE onefile, raíz del proyecto en fuente
_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[4]))

FONDO = _BASE / "assets" / "hoja_proceso_reencauche_v.png"

# ── Calibración de impresión (data/impresion_config.json) ──────────────
# zona_x_mm / zona_y_mm: desplazamiento GLOBAL de todo el formulario
# (mm desde el inicio del área imprimible).
# campos: {campo: {"dx": mm, "dy": mm}} — ajuste fino por campo.
CONFIG_PATH = settings.DATA_DIR / "impresion_config.json"


def _cargar_config() -> tuple[float, float, dict[str, dict[str, float]]]:
    """Devuelve (zona_x_mm, zona_y_mm, offsets_por_campo).

    Lee con utf-8-sig para tolerar BOM (evita caer a valores por defecto
    si el archivo fue editado por herramientas que añaden BOM).
    """
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
        zona_x = float(data.get("zona_x_mm", 0.0))
        zona_y = float(data.get("zona_y_mm", 0.0))
        offsets = data.get("campos", {}) or {}
        return zona_x, zona_y, offsets
    except Exception:
        return 0.0, 0.0, {}


def _guardar_config(
    zona_x: float, zona_y: float, offsets: dict[str, dict[str, float]]
) -> None:
    """Guarda la calibración actual en el JSON."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(
            {"zona_x_mm": zona_x, "zona_y_mm": zona_y, "campos": offsets},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _mm(x_pct: float, y_pct: float, w_pct: float, h_pct: float) -> QRectF:
    """Convierte porcentajes de la hoja (0-100) a un QRectF en milímetros."""
    pw, ph = PAGINA_MM
    return QRectF(x_pct / 100 * pw, y_pct / 100 * ph,
                  w_pct / 100 * pw, h_pct / 100 * ph)


# ── Posiciones de los campos (rectángulos en mm, texto horizontal) ─────
# Coordenadas DETECTADAS del formulario físico (hoja_proceso_reencauche_v.png):
# las casillas de datos empiezan en X=10.9% (tras la franja de título vertical
# izquierda) y terminan en X=94%. Estructura verificada:
#   Talón:  r1 Cliente [10.9-94] | r2 Tiquete|Dimensión|Diseño | r3 O.S.|Serie
#   Cuerpo: r1 Cliente | r2 Tiquete|Dimensión|Marca | r3 Diseño|Serie|Fecha |
#           r4 O.S.|Observación
CAMPOS: dict[str, tuple[QRectF, str]] = {
    # Talón (bloque 1) — parte superior
    "talon_cliente":   (_mm(12.0, 2.8, 80.0, 3.4), "cliente"),
    "talon_tiquete":   (_mm(12.5, 7.2, 31.0, 2.4), "tiquete"),
    "talon_dimension": (_mm(47.5, 7.2, 27.0, 2.4), "dimension"),
    "talon_diseno":    (_mm(78.0, 7.2, 14.0, 2.4), "diseno"),
    "talon_os":        (_mm(12.5, 10.3, 31.0, 2.4), "os"),
    "talon_serie":     (_mm(47.5, 10.3, 44.0, 2.4), "serie"),
    # Cuerpo (bloque 2) — debajo del talón
    "cuerpo_cliente":  (_mm(12.0, 15.4, 80.0, 2.4), "cliente"),
    "cuerpo_tiquete":  (_mm(12.5, 18.4, 22.0, 2.4), "tiquete"),
    "cuerpo_dimension": (_mm(38.5, 18.4, 30.0, 2.4), "dimension"),
    "cuerpo_marca":    (_mm(72.0, 18.4, 20.0, 2.4), "marca"),
    "cuerpo_diseno":   (_mm(12.5, 21.7, 22.0, 2.4), "diseno"),
    "cuerpo_serie":    (_mm(38.5, 21.7, 30.0, 2.4), "serie"),
    "cuerpo_fecha":    (_mm(72.0, 21.7, 20.0, 2.4), "fecha"),
    "cuerpo_os":       (_mm(12.5, 25.0, 22.0, 2.4), "os"),
}

# ── Tamaño de fuente: FIJO 15 pt para TODOS los campos ──────────────────
# Se ignora el tamaño de las casillas: todo sale a 15 pt, sin auto-ajuste.
FONT_SIZE_PT = 15

# ── Excepción: SOLO el campo marca a 10 pt ─────────────────────────────
FONT_SIZE_EXTRA: dict[str, int] = {
    "marca": 10,
}

# ── Diseño: SIEMPRE 20 pt (igual que los números del tiquete) ───────────
# El auto-ajuste lo reducía en la casilla angosta del talón → dos tamaños.
# Con tamaño FIJO + TextDontClip sale a 20 pt en el talón y en el cuerpo.
FONT_SIZE_FIJO: dict[str, int] = {
    "diseno": 20,
}

# ── Marcas cuyo catálogo guarda la SIGLA en vez del nombre completo ────
# Se completan aquí las conocidas; el resto sale del catálogo (nombre real).
MARCAS_SIGLA_A_COMPLETA: dict[str, str] = {
    "HNK": "HANKOOK",
    "TRZ": "TRAZANO",
}


def _valor_marca(llanta) -> str:
    """Nombre COMPLETO de la marca (catálogo), nunca la sigla del campo libre."""
    if hasattr(llanta, "marca_obj") and llanta.marca_obj:
        nombre = (llanta.marca_obj.nombre or "").strip()
        if nombre:
            clave = nombre.upper()
            return MARCAS_SIGLA_A_COMPLETA.get(clave, nombre)
    libre = (llanta.marca or "").strip()
    if libre:
        clave = libre.upper()
        return MARCAS_SIGLA_A_COMPLETA.get(clave, libre)
    return "—"


class TiquetePrinter:
    """Imprime la hoja de proceso con los datos de la llanta superpuestos."""

    @staticmethod
    def print_tiquete(llanta: Llanta, parent_widget=None) -> tuple[bool, str]:
        """Imprime la hoja de proceso de reencauche con los datos de la llanta.

        Usa el tamaño de papel del driver (Carta, soportado por las impresoras
        instaladas) y dibuja el contenido en la zona izquierda de 103 mm.
        Devuelve (success, message).
        """
        if not llanta:
            return False, "No hay datos de llanta para imprimir"

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        # Carta: único tamaño físico soportado por los drivers instalados cuya
        # altura (279.4 mm) coincide con la hoja de proceso (279 mm).
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        # 300 DPI: raster 16x menor que 1200 DPI, evita saturar al driver.
        printer.setResolution(300)

        dialog = QPrintDialog(printer, parent_widget)
        dialog.setWindowTitle("Imprimir Hoja de Proceso")
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return False, "Impresión cancelada"

        # Verificar que la impresora elegida esté operativa antes de enviar
        estado = QPrinterInfo.printerInfo(printer.printerName()).state()
        if estado in (QPrinter.PrinterState.Error, QPrinter.PrinterState.Aborted):
            return False, (
                f"La impresora '{printer.printerName()}' está en estado de error. "
                "Revise en Windows: cola de impresión, impresora encendida y "
                "sin atascos de papel."
            )

        datos = TiquetePrinter._datos_llanta(llanta)
        zona_x, zona_y, offsets = _cargar_config()

        painter = QPainter()
        try:
            if not painter.begin(printer):
                return False, (
                    "La impresora no aceptó el trabajo. Revise en Windows: "
                    "cola de impresión, impresora encendida y sin errores."
                )

            TiquetePrinter._render(painter, printer.resolution(), datos,
                                   zona_x, zona_y, offsets)
        except Exception as e:
            return False, f"Error al imprimir: {e}"
        finally:
            painter.end()

        return True, "Hoja de proceso enviada a la impresora"

    # ── Render (fondo + cuadrícula + datos) ─────────────────────────────

    @staticmethod
    def _render(
        painter: QPainter,
        res: int,
        datos: dict[str, str],
        zona_x: float = 0.0,
        zona_y: float = 0.0,
        offsets: dict[str, dict[str, float]] | None = None,
        grid: bool = False,
    ) -> None:
        """Dibuja el formulario completo en el painter, con calibración.

        - zona_x/zona_y: desplazamiento global (mm) de todo el formulario.
        - offsets: {campo: {"dx": mm, "dy": mm}} — ajuste fino por campo.
        - grid: dibuja una cuadrícula roja de 10 mm para calibrar.
        """
        dpm = res / 25.4  # píxeles de dispositivo por milímetro
        # Origen al inicio de la zona del formulario (calibración global)
        painter.translate(zona_x * dpm, zona_y * dpm)

        # NO se imprime el fondo del formulario: la hoja física YA viene
        # pre-impresa con el formato aprobado. Solo se superponen los datos.
        if grid:
            TiquetePrinter._dibujar_grid(painter, res)
        TiquetePrinter._dibujar_datos(painter, datos, res, offsets or {})

    @staticmethod
    def _dibujar_grid(painter: QPainter, res: int) -> None:
        """Cuadrícula roja de 10 mm sobre la zona del formulario (calibración)."""
        dpm = res / 25.4
        painter.setPen(QPen(Qt.GlobalColor.red, 0.3 * dpm))
        w_px, h_px = PAGINA_MM[0] * dpm, PAGINA_MM[1] * dpm
        gx = 0.0
        while gx <= w_px:
            painter.drawLine(QPointF(gx, 0), QPointF(gx, h_px))
            gx += 10.0 * dpm
        gy = 0.0
        while gy <= h_px:
            painter.drawLine(QPointF(0, gy), QPointF(w_px, gy))
            gy += 10.0 * dpm
        painter.setPen(QPen(Qt.GlobalColor.black, 1.0))

    # ── Vista previa y prueba de calibración ────────────────────────────

    @staticmethod
    def vista_previa(
        llanta,
        zona_x: float,
        zona_y: float,
        offsets: dict[str, dict[str, float]],
        parent_widget=None,
    ) -> None:
        """Abre la vista previa de impresión con la calibración actual."""
        printer = TiquetePrinter._crear_printer()
        preview = QPrintPreviewDialog(printer, parent_widget)
        preview.setWindowTitle("Vista previa — Hoja de Proceso")
        datos = TiquetePrinter._datos_llanta(llanta) if llanta else {}
        preview.paintRequested.connect(
            lambda p: TiquetePrinter._render(
                QPainter(p), p.resolution(), datos, zona_x, zona_y, offsets
            )
        )
        preview.exec()

    @staticmethod
    def imprimir_prueba(
        zona_x: float,
        zona_y: float,
        offsets: dict[str, dict[str, float]],
        parent_widget=None,
    ) -> tuple[bool, str]:
        """Imprime cuadrícula + formulario para calibrar contra el papel físico."""
        printer = TiquetePrinter._crear_printer()
        dialog = QPrintDialog(printer, parent_widget)
        dialog.setWindowTitle("Imprimir Prueba de Calibración")
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return False, "Impresión cancelada"

        estado = QPrinterInfo.printerInfo(printer.printerName()).state()
        if estado in (QPrinter.PrinterState.Error, QPrinter.PrinterState.Aborted):
            return False, (
                f"La impresora '{printer.printerName()}' está en estado de error. "
                "Revise en Windows: cola de impresión e impresora encendida."
            )

        painter = QPainter()
        try:
            if not painter.begin(printer):
                return False, "La impresora no aceptó el trabajo."
            TiquetePrinter._render(painter, printer.resolution(), {},
                                   zona_x, zona_y, offsets, grid=True)
        except Exception as e:
            return False, f"Error al imprimir: {e}"
        finally:
            painter.end()
        return True, "Prueba enviada a la impresora"

    @staticmethod
    def _crear_printer() -> QPrinter:
        """Crea el QPrinter con la configuración de impresión correcta."""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        # Carta: único tamaño físico soportado por los drivers instalados cuya
        # altura (279.4 mm) coincide con la hoja de proceso (279 mm).
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        # 300 DPI: raster 16x menor que 1200 DPI, evita saturar al driver.
        printer.setResolution(300)
        return printer

    # ── Fondo (formato aprobado) ───────────────────────────────────────

    @staticmethod
    def _dibujar_fondo(painter: QPainter, res: int) -> None:
        """Dibuja la hoja escaneada como fondo, pre-escalada a la resolución."""
        dpm = res / 25.4
        zona = QRectF(0, 0, PAGINA_MM[0] * dpm, PAGINA_MM[1] * dpm)

        if not FONDO.exists():
            painter.fillRect(zona, Qt.GlobalColor.white)
            painter.drawRect(zona)
            return

        pix = QPixmap(str(FONDO))
        if pix.isNull():
            painter.fillRect(zona, Qt.GlobalColor.white)
            return

        # Pre-escalar el fondo al tamaño físico de la zona (evita re-escalados
        # pesados por cada paint y reduce el raster enviado al driver).
        target_w = int(PAGINA_MM[0] * dpm)
        target_h = int(PAGINA_MM[1] * dpm)
        pix = pix.scaled(
            target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(zona, pix, QRectF(pix.rect()))

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
        marca = _valor_marca(llanta)
        fecha = (
            llanta.fecha_ingreso.strftime("%d/%m/%y")
            if getattr(llanta, "fecha_ingreso", None)
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
            "marca": marca,
            "fecha": fecha,
        }

    # ── Overlay de datos ───────────────────────────────────────────────

    @staticmethod
    def _dibujar_datos(
        painter: QPainter,
        datos: dict[str, str],
        res: int,
        offsets: dict[str, dict[str, float]] | None = None,
    ) -> None:
        """Escribe cada dato en su caja (texto horizontal, como el llenado real).

        offsets: {campo: {"dx": mm, "dy": mm}} — ajuste fino por campo
        (calibración desde data/impresion_config.json).
        """
        offsets = offsets or {}
        dpm = res / 25.4
        for campo, (rect_mm, clave) in CAMPOS.items():
            valor = (datos.get(clave, "") or "").upper()
            if not valor or valor == "—":
                continue
            off = offsets.get(campo, {}) or {}
            dx = float(off.get("dx", 0.0)) * dpm
            dy = float(off.get("dy", 0.0)) * dpm
            # Tamaño FIJO: 15 pt para todos; SOLO "marca" a 12 pt.
            # TextDontClip: si un valor excede la casilla, se dibuja completo.
            fuente = QFont("Arial", FONT_SIZE_EXTRA.get(clave, FONT_SIZE_PT))
            fuente.setBold(True)
            flags = int(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                | Qt.TextFlag.TextDontClip
            )
            painter.setFont(fuente)
            painter.setPen(Qt.GlobalColor.black)
            # Texto horizontal centrado verticalmente, alineado a la izquierda
            rect_px = QRectF(
                rect_mm.x() * dpm + dx, rect_mm.y() * dpm + dy,
                rect_mm.width() * dpm, rect_mm.height() * dpm,
            )
            painter.drawText(
                rect_px.adjusted(dpm, 0, -dpm, 0),
                flags,
                valor,
            )

    @staticmethod
    def _fuente_para(
        painter: QPainter,
        texto: str,
        rect_mm: QRectF,
        res: int,
        max_size: int = 20,
    ) -> QFont:
        """Elige un tamaño de fuente que quepa en la caja (píxeles vs píxeles).

        max_size: tamaño máximo en pt para el campo (se reduce solo si el
        dato no cabe). Default 20 = negrilla MUY visible.
        """
        limite_px = rect_mm.width() * (res / 25.4) * 0.92
        for size in range(max_size, 7, -2):
            font = QFont("Arial", size)
            font.setBold(True)
            painter.setFont(font)
            fm = painter.fontMetrics()
            if fm.horizontalAdvance(texto) <= limite_px:
                return font
        return QFont("Arial", 5)