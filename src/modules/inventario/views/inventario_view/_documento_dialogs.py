"""Diálogos de líneas de producto y visualización de documentos de inventario."""

from datetime import datetime
from decimal import Decimal
from typing import cast

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
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

from src.modules.inventario.models.producto_model import Producto
from src.modules.inventario.services.documento_service import DocumentoService
from src.modules.inventario.views.inventario_view._widgets import C_AZUL


class _LineaProductoDialog(QDialog):
    """Agrega un producto a un documento de movimiento."""

    def __init__(
        self,
        productos: list[Producto],
        tipo: str,  # "ENTRADA" or "SALIDA"
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Agregar Producto")
        self.resize(380, 200)
        layout = QFormLayout()

        self.producto_combo = QComboBox()
        for p in productos:
            stock_str = f" (stock: {p.stock})" if tipo == "SALIDA" else ""
            self.producto_combo.addItem(
                f"{p.nombre} ({p.sku}){stock_str}", p.id
            )
        layout.addRow("Producto:", self.producto_combo)

        self.cantidad_input = QLineEdit()
        self.cantidad_input.setPlaceholderText("0")
        layout.addRow("Cantidad *:", self.cantidad_input)

        self.costo_input = QLineEdit()
        self.costo_input.setPlaceholderText("Dejar vacío = costo actual")
        layout.addRow("Costo Unit.:", self.costo_input)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self._validar)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

        self.setLayout(layout)

    def _validar(self) -> None:
        text = self.cantidad_input.text().strip()
        if not text:
            QMessageBox.warning(self, "Validación", "Ingrese la cantidad")
            return
        try:
            cant = Decimal(text)
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad inválida")
            return
        if cant <= 0:
            QMessageBox.warning(self, "Validación", "La cantidad debe ser > 0")
            return
        self.accept()

    def get_data(self) -> tuple[int, Decimal, Decimal | None]:
        pid = self.producto_combo.currentData()
        cantidad = Decimal(self.cantidad_input.text().strip() or "0")
        costo_text = self.costo_input.text().strip()
        costo = Decimal(costo_text) if costo_text else None
        return pid, cantidad, costo


# ═════════════════════════════════════════════════════════════════════
#  Document search / viewer dialog
# ═════════════════════════════════════════════════════════════════════

class _DocumentoSearchDialog(QDialog):
    """Search and view inventory documents."""

    COLUMNAS = ["Documento", "Tipo", "Fecha", "Movimientos", "Observaciones"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Búsqueda de Documentos")
        self.resize(750, 500)
        layout = QVBoxLayout()

        # ── Filters ──────────────────────────────────────────────────
        filter_group = QFrame()
        filter_group.setStyleSheet("QFrame { background: #f8f9fa; border-radius: 6px; padding: 6px; }")
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(8, 6, 8, 6)

        self.filtro_numero = QLineEdit()
        self.filtro_numero.setPlaceholderText("N° documento...")
        self.filtro_numero.setStyleSheet("max-width: 180px;")
        filter_layout.addWidget(QLabel("Número:"))
        filter_layout.addWidget(self.filtro_numero)

        self.filtro_tipo = QComboBox()
        self.filtro_tipo.addItems(["TODOS", "COMPRA", "PRODUCCION"])
        filter_layout.addWidget(QLabel("Tipo:"))
        filter_layout.addWidget(self.filtro_tipo)

        self.filtro_desde = QDateEdit()
        self.filtro_desde.setCalendarPopup(True)
        self.filtro_desde.setDate(QDate.currentDate().addMonths(-1))
        filter_layout.addWidget(QLabel("Desde:"))
        filter_layout.addWidget(self.filtro_desde)

        self.filtro_hasta = QDateEdit()
        self.filtro_hasta.setCalendarPopup(True)
        self.filtro_hasta.setDate(QDate.currentDate())
        filter_layout.addWidget(QLabel("Hasta:"))
        filter_layout.addWidget(self.filtro_hasta)

        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.clicked.connect(self._buscar)
        btn_buscar.setStyleSheet(
            f"QPushButton {{ background: {C_AZUL}; color: white; font-weight: bold; "
            "padding: 6px 14px; border-radius: 4px; border: none; }}"
        )
        filter_layout.addWidget(btn_buscar)

        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)

        # ── Results table ────────────────────────────────────────────
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.itemDoubleClicked.connect(self._ver_detalle)
        layout.addWidget(self.tabla)

        # ── Bottom ──────────────────────────────────────────────────
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

        self.setLayout(layout)

        # Load initial results
        self._buscar()

    def _buscar(self) -> None:
        numero = self.filtro_numero.text().strip() or None
        tipo_text = self.filtro_tipo.currentText()
        tipo = tipo_text if tipo_text != "TODOS" else None
        desde = cast(datetime, self.filtro_desde.date().toPython())
        hasta = cast(datetime, self.filtro_hasta.date().toPython())

        docs = DocumentoService.buscar_documentos(
            numero=numero,
            tipo=tipo,
            fecha_desde=desde,
            fecha_hasta=hasta,
        )
        self.tabla.setRowCount(len(docs))
        for row, d in enumerate(docs):
            self.tabla.setItem(row, 0, QTableWidgetItem(d.numero_documento))
            self.tabla.setItem(row, 1, QTableWidgetItem(d.tipo))
            self.tabla.setItem(row, 2, QTableWidgetItem(d.fecha.isoformat()))
            mov_count = len(d.movimientos) if d.movimientos else 0
            self.tabla.setItem(row, 3, QTableWidgetItem(str(mov_count)))
            self.tabla.setItem(row, 4, QTableWidgetItem(d.observaciones or ""))
            # Store id in first column user role
            self.tabla.item(row, 0).setData(Qt.ItemDataRole.UserRole, d.id)

    def _ver_detalle(self) -> None:
        row = self.tabla.currentRow()
        if row < 0:
            return
        doc_id = self.tabla.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not doc_id:
            return
        dlg = _DocumentoDetalleDialog(doc_id, self)
        dlg.exec()


class _DocumentoDetalleDialog(QDialog):
    """Shows the line items of a single document."""

    COLUMNAS = ["Producto", "SKU", "Tipo", "Cantidad", "Costo Unit.", "Total", "Fecha"]

    def __init__(self, documento_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        doc = DocumentoService.obtener_documento(documento_id)
        if not doc:
            QMessageBox.warning(self, "Error", "Documento no encontrado")
            self.reject()
            return

        self.setWindowTitle(f"Documento: {doc.numero_documento}")
        self.resize(650, 400)
        layout = QVBoxLayout()

        # Header info
        info = QLabel(
            f"<b>Documento:</b> {doc.numero_documento}   |   "
            f"<b>Tipo:</b> {doc.tipo}   |   "
            f"<b>Fecha:</b> {doc.fecha.isoformat()}"
        )
        info.setStyleSheet("font-size: 13px; padding: 8px; background: #f8f9fa; border-radius: 6px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Movements table
        movs = DocumentoService.obtener_movimientos_por_documento(documento_id)
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)

        self.tabla.setRowCount(len(movs))
        for row, m in enumerate(movs):
            producto = m.producto
            total = float(m.cantidad) * float(m.costo_unitario)
            self.tabla.setItem(row, 0, QTableWidgetItem(producto.nombre if producto else f"#{m.producto_id}"))
            self.tabla.setItem(row, 1, QTableWidgetItem(producto.sku if producto else ""))
            self.tabla.setItem(row, 2, QTableWidgetItem(m.tipo))
            self.tabla.setItem(row, 3, QTableWidgetItem(str(m.cantidad)))
            self.tabla.setItem(row, 4, QTableWidgetItem(f"${float(m.costo_unitario):,.2f}"))
            self.tabla.setItem(row, 5, QTableWidgetItem(f"${total:,.2f}"))
            self.tabla.setItem(row, 6, QTableWidgetItem(m.fecha.strftime("%d/%m/%Y %H:%M") if m.fecha else ""))

        layout.addWidget(self.tabla)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

        self.setLayout(layout)