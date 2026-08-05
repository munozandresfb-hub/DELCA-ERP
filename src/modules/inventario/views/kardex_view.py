"""Kardex / Inventory movement ledger — registration and consultation.

This is the central tool for manually recording raw-material entries (purchases),
exits (production consumption), adjustments, and waste, so the system stock always
matches physical plant stock.
"""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from PySide6.QtCore import QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import openpyxl
HAS_OPENPYXL = True

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None  # type: ignore[assignment]

from src.modules.inventario.models.movimiento_inventario_model import (
    MovimientoInventario,
)
from src.modules.inventario.services.producto_service import ProductoService


class KardexView(QWidget):
    """Kardex — movement ledger with registration and consultation."""

    COLUMNAS = [
        "ID", "Fecha", "Producto", "SKU", "Tipo",
        "Cantidad", "Costo Unit.", "Saldo", "Referencia", "Observaciones",
    ]

    TIPOS_MOVIMIENTO = ["ENTRADA", "SALIDA", "MERMA", "AJUSTE"]

    def __init__(self) -> None:
        super().__init__()
        self._productos_cache: list[dict] = []
        self._all_movements: list[MovimientoInventario] = []
        self.setup_ui()
        self._safe_cargar_inicial()

    def _safe_cargar_inicial(self) -> None:
        try:
            self._cargar_productos()
        except Exception as e:
            print(f"[KardexView] Error cargando productos: {e}")
        try:
            self._cargar_datos()
        except Exception as e:
            print(f"[KardexView] Error cargando datos: {e}")

    # ── UI Setup ────────────────────────────────────────────────────

    def setup_ui(self) -> None:
        layout = QVBoxLayout()

        # Header
        header = QLabel("Kardex / Movimientos de Inventario")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px 0;")
        layout.addWidget(header)

        # ── Toolbar (action buttons) ────────────────────────────────
        toolbar = QHBoxLayout()

        btn_ingreso = QPushButton("➕ Ingreso manual")
        btn_ingreso.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_ingreso.clicked.connect(lambda: self._abrir_formulario("ENTRADA"))

        btn_salida = QPushButton("➖ Salida manual")
        btn_salida.setStyleSheet(
            "QPushButton { background: #e74c3c; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_salida.clicked.connect(lambda: self._abrir_formulario("SALIDA"))

        btn_ajuste = QPushButton("🔧 Ajuste")
        btn_ajuste.setStyleSheet(
            "QPushButton { background: #f39c12; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_ajuste.clicked.connect(lambda: self._abrir_formulario("AJUSTE"))

        btn_merma = QPushButton("📋 Merma")
        btn_merma.setStyleSheet(
            "QPushButton { background: #e67e22; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_merma.clicked.connect(lambda: self._abrir_formulario("MERMA"))

        toolbar.addWidget(btn_ingreso)
        toolbar.addWidget(btn_salida)
        toolbar.addWidget(btn_ajuste)
        toolbar.addWidget(btn_merma)

        # ── Export buttons ───────────────────────────────────────────
        separator = QLabel("  │  ")
        separator.setStyleSheet("color: #ccc; padding: 0 4px;")
        toolbar.addWidget(separator)

        btn_excel = QPushButton("📊 Exportar Excel")
        btn_excel.setStyleSheet(
            "QPushButton { background: #1d6f42; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_excel.clicked.connect(self._exportar_excel)

        btn_pdf = QPushButton("📄 Exportar PDF")
        btn_pdf.setStyleSheet(
            "QPushButton { background: #8b0000; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_pdf.clicked.connect(self._exportar_pdf)

        toolbar.addWidget(btn_excel)
        toolbar.addWidget(btn_pdf)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # ── Filters ─────────────────────────────────────────────────
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("Producto:"))
        self.producto_combo = QComboBox()
        self.producto_combo.addItem("Todos", None)
        self.producto_combo.setMinimumWidth(220)
        self.producto_combo.currentIndexChanged.connect(self._cargar_datos)
        filter_row.addWidget(self.producto_combo)

        filter_row.addWidget(QLabel("Tipo:"))
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["Todos", "ENTRADA", "SALIDA", "MERMA", "AJUSTE"])
        self.tipo_combo.currentIndexChanged.connect(self._cargar_datos)
        filter_row.addWidget(self.tipo_combo)

        filter_row.addWidget(QLabel("Desde:"))
        self.fecha_desde = QDateEdit()
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_desde.dateChanged.connect(self._cargar_datos)
        filter_row.addWidget(self.fecha_desde)

        filter_row.addWidget(QLabel("Hasta:"))
        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setCalendarPopup(True)
        self.fecha_hasta.setDate(QDate.currentDate())
        self.fecha_hasta.dateChanged.connect(self._cargar_datos)
        filter_row.addWidget(self.fecha_hasta)

        btn_refresh = QPushButton("🔄")
        btn_refresh.setStyleSheet("font-size: 14px; padding: 4px 12px;")
        btn_refresh.clicked.connect(self._cargar_datos)
        filter_row.addWidget(btn_refresh)

        filter_row.addStretch()
        layout.addLayout(filter_row)

        # ── Table ───────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNAS))
        self.table.setHorizontalHeaderLabels(self.COLUMNAS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self.setLayout(layout)

    # ── Data Loading ────────────────────────────────────────────────

    def _cargar_productos(self) -> None:
        productos = ProductoService.listar_productos(solo_activos=True)
        self._productos_cache = []
        self.producto_combo.clear()
        self.producto_combo.addItem("Todos", None)
        for p in productos:
            label = f"{p.nombre} ({p.sku})"
            self.producto_combo.addItem(label, p.id)
            self._productos_cache.append({
                "id": p.id,
                "nombre": p.nombre,
                "sku": p.sku,
            })

    def _cargar_datos(self) -> None:
        producto_id = self.producto_combo.currentData()
        tipo = self.tipo_combo.currentText()
        desde = self.fecha_desde.date().toPython()
        hasta = self.fecha_hasta.date().toPython()
        desde_dt = datetime(desde.year, desde.month, desde.day, 0, 0, 0)
        hasta_dt = datetime(hasta.year, hasta.month, hasta.day, 23, 59, 59)

        self._all_movements = ProductoService.obtener_kardex_por_filtros(
            producto_id=producto_id,
            tipo=tipo if tipo != "Todos" else None,
            fecha_desde=desde_dt,
            fecha_hasta=hasta_dt,
            limite=500,
        )
        self._render_tabla()

    # ── Table Rendering ─────────────────────────────────────────────

    def _render_tabla(self) -> None:
        movs = self._all_movements
        self.table.setRowCount(len(movs))

        # Running balance: process ASC (oldest first)
        saldo = Decimal("0")
        saldos: dict[int, Decimal] = {}
        for m in sorted(movs, key=lambda x: x.fecha or datetime.min):
            if m.tipo == "ENTRADA":
                saldo += m.cantidad
            elif m.tipo in ("SALIDA", "MERMA"):
                saldo -= m.cantidad
            elif m.tipo == "AJUSTE":
                saldo = m.cantidad
            saldos[m.id] = saldo

        # Render in DESC order (newest first)
        for row, m in enumerate(movs):
            prod = self._buscar_producto(m.producto_id)

            self.table.setItem(row, 0, QTableWidgetItem(str(m.id)))
            self.table.setItem(
                row, 1,
                QTableWidgetItem(m.fecha.strftime("%Y-%m-%d %H:%M") if m.fecha else ""),
            )
            self.table.setItem(row, 2, QTableWidgetItem(prod["nombre"] if prod else ""))
            self.table.setItem(row, 3, QTableWidgetItem(prod["sku"] if prod else ""))
            self.table.setItem(row, 4, QTableWidgetItem(m.tipo or ""))

            # Cantidad with sign
            if m.tipo == "ENTRADA":
                cant_str = f"+{m.cantidad}"
            elif m.tipo in ("SALIDA", "MERMA"):
                cant_str = f"-{m.cantidad}"
            else:
                cant_str = str(m.cantidad)
            self.table.setItem(row, 5, QTableWidgetItem(cant_str))

            self.table.setItem(
                row, 6,
                QTableWidgetItem(f"${m.costo_unitario:,.2f}" if m.costo_unitario else "$0"),
            )

            # Saldo
            saldo_actual = saldos.get(m.id, Decimal("0"))
            self.table.setItem(row, 7, QTableWidgetItem(f"{saldo_actual:,.2f}"))

            self.table.setItem(row, 8, QTableWidgetItem(m.referencia or ""))
            self.table.setItem(row, 9, QTableWidgetItem(m.observaciones or ""))

            # Color coding
            color = None
            if m.tipo == "ENTRADA":
                color = "#d5f5e3"  # soft green
            elif m.tipo in ("SALIDA", "MERMA"):
                color = "#fadbd8"  # soft red
            elif m.tipo == "AJUSTE":
                color = "#fcf3cf"  # soft yellow

            if color:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor(color))

        self.table.setColumnHidden(0, True)

    def _buscar_producto(self, producto_id: int) -> dict | None:
        for p in self._productos_cache:
            if p["id"] == producto_id:
                return p
        return None

    # ── Export ────────────────────────────────────────────────────────

    def _exportar_excel(self) -> None:
        if not HAS_OPENPYXL:
            QMessageBox.warning(
                self, "Exportar Excel",
                "openpyxl no está instalado.\nEjecute: pip install openpyxl",
            )
            return

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar como Excel", "kardex.xlsx",
            "Excel (*.xlsx)",
        )
        if not ruta:
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Kardex"

        # Header row
        header_font = openpyxl.styles.Font(bold=True, color="FFFFFF")
        header_fill = openpyxl.styles.PatternFill(
            start_color="2c3e50", end_color="2c3e50", fill_type="solid",
        )
        for col, titulo in enumerate(self.COLUMNAS, 1):
            cell = ws.cell(row=1, column=col, value=titulo)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = openpyxl.styles.Alignment(horizontal="center")

        # Data rows
        for row, m in enumerate(self._all_movements, 2):
            prod = self._buscar_producto(m.producto_id)
            ws.cell(row=row, column=1, value=m.id)
            ws.cell(
                row=row, column=2,
                value=m.fecha.strftime("%Y-%m-%d %H:%M") if m.fecha else "",
            )
            ws.cell(row=row, column=3, value=prod["nombre"] if prod else "")
            ws.cell(row=row, column=4, value=prod["sku"] if prod else "")
            ws.cell(row=row, column=5, value=m.tipo or "")

            if m.tipo == "ENTRADA":
                cant_str = f"+{m.cantidad}"
            elif m.tipo in ("SALIDA", "MERMA"):
                cant_str = f"-{m.cantidad}"
            else:
                cant_str = str(m.cantidad)
            ws.cell(row=row, column=6, value=cant_str)

            ws.cell(
                row=row, column=7,
                value=float(m.costo_unitario) if m.costo_unitario else 0,
            )
            ws.cell(row=row, column=8, value="")

            # Calculate running balance (same logic as _render_tabla)
            ws.cell(row=row, column=8, value="")  # placeholder
            ws.cell(row=row, column=9, value=m.referencia or "")
            ws.cell(row=row, column=10, value=m.observaciones or "")

        # Column widths
        widths = [6, 18, 30, 12, 10, 12, 14, 14, 20, 35]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

        wb.save(ruta)
        QMessageBox.information(
            self, "Exportar Excel",
            f"✓ Exportado correctamente:\n{os.path.basename(ruta)}",
        )

    def _exportar_pdf(self) -> None:
        if FPDF is None:
            QMessageBox.warning(
                self, "Exportar PDF",
                "fpdf2 no está instalado.\nEjecute: pip install fpdf2",
            )
            return

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar como PDF", "kardex.pdf",
            "PDF (*.pdf)",
        )
        if not ruta:
            return

        pdf = FPDF(orientation="L", unit="mm", format="A4")
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)

        # Title
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 8, "KARDEX - MOVIMIENTOS DE INVENTARIO", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        desde_str = self.fecha_desde.date().toString("yyyy-MM-dd")
        hasta_str = self.fecha_hasta.date().toString("yyyy-MM-dd")
        filtros = f"Filtro: {desde_str} al {hasta_str}"
        if self.producto_combo.currentIndex() > 0:
            filtros += f" | Producto: {self.producto_combo.currentText()}"
        if self.tipo_combo.currentIndex() > 0:
            filtros += f" | Tipo: {self.tipo_combo.currentText()}"
        pdf.cell(0, 6, filtros, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Column widths (landscape A4 = 297mm, margins ~10mm each)
        col_widths = [8, 22, 40, 18, 14, 16, 18, 20, 28, 50]
        headers = self.COLUMNAS

        # Table header
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_fill_color(44, 62, 80)
        pdf.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 6, h, border=1, align="C", fill=True)
        pdf.ln()

        # Table rows
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(0, 0, 0)

        # Calculate running balance for PDF
        saldo = Decimal("0")
        saldos: dict[int, Decimal] = {}
        for m in sorted(self._all_movements, key=lambda x: x.fecha or datetime.min):
            if m.tipo == "ENTRADA":
                saldo += m.cantidad
            elif m.tipo in ("SALIDA", "MERMA"):
                saldo -= m.cantidad
            elif m.tipo == "AJUSTE":
                saldo = m.cantidad
            saldos[m.id] = saldo

        for m in self._all_movements:
            prod = self._buscar_producto(m.producto_id)
            row_data = [
                str(m.id),
                m.fecha.strftime("%Y-%m-%d") if m.fecha else "",
                prod["nombre"] if prod else "",
                prod["sku"] if prod else "",
                m.tipo or "",
                str(m.cantidad),
                f"${m.costo_unitario:,.0f}" if m.costo_unitario else "",
                f"{saldos.get(m.id, 0):,.0f}",
                m.referencia or "",
                m.observaciones or "",
            ]

            # Check page break
            if pdf.get_y() + 6 > pdf.page_break_trigger:
                pdf.add_page()
                # Reprint header
                pdf.set_font("Helvetica", "B", 7)
                pdf.set_fill_color(44, 62, 80)
                pdf.set_text_color(255, 255, 255)
                for i, h in enumerate(headers):
                    pdf.cell(col_widths[i], 6, h, border=1, align="C", fill=True)
                pdf.ln()
                pdf.set_font("Helvetica", "", 6.5)
                pdf.set_text_color(0, 0, 0)

            # Row background
            if m.tipo == "ENTRADA":
                pdf.set_fill_color(213, 245, 227)
            elif m.tipo in ("SALIDA", "MERMA"):
                pdf.set_fill_color(250, 219, 216)
            elif m.tipo == "AJUSTE":
                pdf.set_fill_color(252, 243, 207)
            else:
                pdf.set_fill_color(255, 255, 255)

            for i, val in enumerate(row_data):
                pdf.cell(col_widths[i], 6, val, border=1, align="C" if i == 0 else "L", fill=True)
            pdf.ln()

        pdf.output(ruta)
        QMessageBox.information(
            self, "Exportar PDF",
            f"✓ Exportado correctamente:\n{os.path.basename(ruta)}",
        )

    # ── Registration ────────────────────────────────────────────────

    def _abrir_formulario(self, tipo: str) -> None:
        dlg = _MovimientoFormDialog(tipo, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar_productos()
            self._cargar_datos()


# ═════════════════════════════════════════════════════════════════════
#  Movement Registration Dialog
# ═════════════════════════════════════════════════════════════════════

class _MovimientoFormDialog(QDialog):
    """Form to register a single inventory movement (ENTRADA/SALIDA/MERMA/AJUSTE)."""

    def __init__(self, tipo: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tipo = tipo
        self.setWindowTitle(self._titulo_para_tipo())
        self.resize(400, 280)
        layout = QFormLayout()

        # Product selector
        self.producto_combo = QComboBox()
        self._cargar_productos()
        layout.addRow("Producto *:", self.producto_combo)

        # Quantity
        self.cantidad_input = QLineEdit()
        self.cantidad_input.setPlaceholderText("0")
        layout.addRow("Cantidad *:", self.cantidad_input)

        # Cost (optional — defaults to current product cost)
        self.costo_input = QLineEdit()
        self.costo_input.setPlaceholderText("Usar costo actual del producto")
        layout.addRow("Costo Unit. $:", self.costo_input)

        # Reference
        self.referencia_input = QLineEdit()
        self.referencia_input.setPlaceholderText("Factura, orden, nota...")
        layout.addRow("Referencia:", self.referencia_input)

        # Observations
        self.obs_input = QLineEdit()
        self.obs_input.setPlaceholderText("Observaciones opcionales")
        layout.addRow("Observaciones:", self.obs_input)

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._guardar)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

        self.setLayout(layout)

    def _titulo_para_tipo(self) -> str:
        titulos = {
            "ENTRADA": "Registrar Ingreso de MP",
            "SALIDA": "Registrar Salida de MP",
            "MERMA": "Registrar Merma",
            "AJUSTE": "Ajustar Stock",
        }
        return titulos.get(self._tipo, f"Registrar {self._tipo}")

    def _cargar_productos(self) -> None:
        self.producto_combo.clear()
        for p in ProductoService.listar_productos(categoria="MATERIA_PRIMA", solo_activos=True):
            label = f"{p.nombre} ({p.sku}) — Stock: {p.stock}"
            self.producto_combo.addItem(label, (p.id, p.costo_unitario))

    def _guardar(self) -> None:
        data = self.producto_combo.currentData()
        if data is None:
            QMessageBox.warning(self, "Validación", "Seleccione un producto")
            return
        producto_id, costo_default = data

        try:
            cantidad = Decimal(self.cantidad_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad inválida")
            return

        if cantidad <= 0 and self._tipo != "AJUSTE":
            QMessageBox.warning(self, "Validación", "La cantidad debe ser > 0")
            return

        try:
            costo = Decimal(self.costo_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Costo inválido")
            return
        if costo == 0:
            costo = costo_default  # fallback to product's current cost

        referencia = self.referencia_input.text().strip() or None
        observaciones = self.obs_input.text().strip() or None

        ok, msg = ProductoService.registrar_movimiento(
            producto_id=producto_id,
            tipo=self._tipo,
            cantidad=cantidad,
            costo_unitario=costo,
            referencia=referencia,
            observaciones=observaciones,
        )
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", str(msg))
