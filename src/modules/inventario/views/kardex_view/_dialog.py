from __future__ import annotations

from decimal import Decimal
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.modules.inventario.services.producto_service import ProductoService


class _MovimientoFormDialog(QDialog):
    """Form to register a single inventory movement (ENTRADA/SALIDA/AJUSTE).

    Cada movimiento registra Cantidad Und (stock) y Cantidad KG (stock_kg).
    ENTRADA: pide N° de factura (crea documento INGRESO).
    SALIDA: pide N° de documento (consecutivo digitado por el usuario — crea
            documento SALIDA).
    AJUSTE: sin documento; fija stock y stock_kg al valor indicado.
    """

    def __init__(self, tipo: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tipo = tipo
        self._es_salida_ajuste = tipo in ("SALIDA", "AJUSTE")
        self.setWindowTitle(self._titulo_para_tipo())
        self.resize(420, 340)
        layout = QFormLayout()

        # Product selector (se carga al final, cuando ya existen todos los widgets)
        self.producto_combo = QComboBox()
        layout.addRow("Producto *:", self.producto_combo)

        # Cantidad Und
        self.cantidad_input = QLineEdit()
        self.cantidad_input.setPlaceholderText("0")
        self.cantidad_input.textChanged.connect(self._sugerir_kg)
        layout.addRow("Cantidad Und *:", self.cantidad_input)

        # Cantidad KG
        self.kg_input = QLineEdit()
        self.kg_input.setPlaceholderText("0")
        layout.addRow("Cantidad KG:", self.kg_input)

        # Cost (solo ENTRADA)
        self.costo_input: QLineEdit | None = None
        if not self._es_salida_ajuste:
            self.costo_input = QLineEdit()
            self.costo_input.setPlaceholderText("Usar costo actual del producto")
            layout.addRow("Costo Unit. $:", self.costo_input)

        # Unidad de medida (SALIDA/AJUSTE) / Referencia (ENTRADA)
        self.referencia_input = QLineEdit()
        if self._es_salida_ajuste:
            self.referencia_input.setReadOnly(True)
            self.referencia_input.setPlaceholderText("Se autocompleta con el producto")
            layout.addRow("Unidad de medida:", self.referencia_input)
        else:
            self.referencia_input.setPlaceholderText("Factura, orden, nota...")
            layout.addRow("Referencia:", self.referencia_input)

        # N° Factura (ENTRADA) / N° Documento (SALIDA)
        self.doc_input = QLineEdit()
        if self._tipo == "ENTRADA":
            self.doc_input.setPlaceholderText("Número de factura")
            layout.addRow("N° Factura *:", self.doc_input)
        elif self._tipo == "SALIDA":
            self.doc_input.setPlaceholderText("Consecutivo del documento")
            layout.addRow("N° Documento *:", self.doc_input)

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

        # Cargar productos al final (referencia_input ya existe para el autocompletado)
        self.producto_combo.currentIndexChanged.connect(self._on_producto_cambiado)
        self._cargar_productos()

    def _titulo_para_tipo(self) -> str:
        titulos = {
            "ENTRADA": "Registrar Ingreso de MP",
            "SALIDA": "Registrar Salida de MP",
            "AJUSTE": "Ajustar Stock",
        }
        return titulos.get(self._tipo, f"Registrar {self._tipo}")

    def _cargar_productos(self) -> None:
        self.producto_combo.clear()
        for p in ProductoService.listar_productos(categoria="MATERIA_PRIMA", solo_activos=True):
            label = f"{p.nombre} ({p.sku}) — Und: {p.stock} | KG: {p.stock_kg}"
            self.producto_combo.addItem(
                label, (p.id, p.costo_unitario, p.unidad_medida, p.stock_kg, p.stock)
            )
        self._on_producto_cambiado()

    def _on_producto_cambiado(self) -> None:
        """Autocompleta la unidad de medida para SALIDA y AJUSTE."""
        if not self._es_salida_ajuste:
            return
        data = self.producto_combo.currentData()
        if data:
            self.referencia_input.setText(str(data[2] or ""))

    def _sugerir_kg(self) -> None:
        """Sugiere la cantidad KG según el ratio KG/und del producto."""
        data = self.producto_combo.currentData()
        if not data:
            return
        _, _, _, stock_kg, stock = data
        try:
            und = Decimal(self.cantidad_input.text() or "0")
        except Exception:
            return
        if und <= 0 or not stock_kg or not stock or float(stock) <= 0:
            return
        ratio = Decimal(str(stock_kg)) / Decimal(str(stock))
        self.kg_input.setText(f"{und * ratio:.2f}")

    def _guardar(self) -> None:
        data = self.producto_combo.currentData()
        if data is None:
            QMessageBox.warning(self, "Validación", "Seleccione un producto")
            return
        producto_id, costo_default, unidad, _, _ = data

        try:
            cantidad = Decimal(self.cantidad_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad Und inválida")
            return
        if cantidad < 0:
            QMessageBox.warning(self, "Validación", "La cantidad Und no puede ser negativa")
            return
        if cantidad == 0 and self._tipo != "AJUSTE":
            QMessageBox.warning(self, "Validación", "La cantidad Und debe ser mayor a cero")
            return

        try:
            cantidad_kg = Decimal(self.kg_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad KG inválida")
            return
        if cantidad_kg < 0:
            QMessageBox.warning(self, "Validación", "La cantidad KG no puede ser negativa")
            return

        # Costo: editable solo en ENTRADA; en SALIDA/AJUSTE se usa el del producto
        if self.costo_input is not None:
            try:
                costo = Decimal(self.costo_input.text() or "0")
            except Exception:
                QMessageBox.warning(self, "Validación", "Costo inválido")
                return
            if costo == 0:
                costo = costo_default
        else:
            costo = costo_default

        # Documento: crear y vincular (factura para ENTRADA, consecutivo para SALIDA)
        documento_id = None
        if self._tipo in ("ENTRADA", "SALIDA"):
            numero = self.doc_input.text().strip()
            if not numero:
                etiqueta = "N° Factura" if self._tipo == "ENTRADA" else "N° Documento"
                QMessageBox.warning(self, "Validación", f"El {etiqueta} es obligatorio")
                return
            ok, res = ProductoService.crear_documento(
                numero_documento=numero,
                tipo="INGRESO" if self._tipo == "ENTRADA" else "SALIDA",
                observaciones=self.obs_input.text().strip() or None,
            )
            if not ok:
                QMessageBox.warning(self, "Error", str(res))
                return
            documento_id = int(res)

        referencia = self.referencia_input.text().strip() or None
        observaciones = self.obs_input.text().strip() or None

        ok, msg = ProductoService.registrar_movimiento(
            producto_id=producto_id,
            tipo=self._tipo,
            cantidad=cantidad,
            cantidad_kg=cantidad_kg,
            costo_unitario=costo,
            referencia=referencia,
            observaciones=observaciones,
            documento_id=documento_id,
        )
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", str(msg))


class _DocumentosDialog(QDialog):
    """Documentos de inventario de materia prima.

    - Documento de INGRESO: se guarda con el número de FACTURA (solicitado al usuario).
    - Documento de SALIDA: se guarda con un número de documento CONSECUTIVO
      (digitado por el usuario).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Documentos de Inventario")
        self.resize(620, 480)
        layout = QVBoxLayout()

        # ── Formulario de registro ──
        form = QFormLayout()

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItem("Documento de Ingreso", "INGRESO")
        self.tipo_combo.addItem("Documento de Salida", "SALIDA")
        self.tipo_combo.currentIndexChanged.connect(self._actualizar_placeholder)
        form.addRow("Tipo de documento:", self.tipo_combo)

        self.numero_input = QLineEdit()
        self.numero_input.setPlaceholderText("Número de factura")
        form.addRow("N° Documento *:", self.numero_input)

        self.fecha_input = QDateEdit()
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setDate(QDate.currentDate())
        form.addRow("Fecha:", self.fecha_input)

        self.obs_input = QLineEdit()
        self.obs_input.setPlaceholderText("Observaciones opcionales")
        form.addRow("Observaciones:", self.obs_input)

        btn_row = QHBoxLayout()
        btn_guardar = QPushButton("💾 Guardar documento")
        btn_guardar.setStyleSheet(
            "QPushButton { background: #2e7d32; color: white; font-weight: bold; "
            "padding: 8px 18px; border-radius: 5px; border: none; }"
        )
        btn_guardar.clicked.connect(self._guardar)
        btn_row.addWidget(btn_guardar)
        btn_row.addStretch()
        form.addRow(btn_row)

        layout.addLayout(form)

        # ── Lista de documentos existentes ──
        layout.addWidget(QLabel("Documentos registrados:"))
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["ID", "N° Documento", "Tipo", "Fecha", "Observaciones"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnHidden(0, True)
        layout.addWidget(self.table)

        # Cerrar
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)
        layout.addWidget(btn_cerrar)

        self.setLayout(layout)
        self._cargar_documentos()

    def _actualizar_placeholder(self) -> None:
        tipo = self.tipo_combo.currentData()
        if tipo == "INGRESO":
            self.numero_input.setPlaceholderText("Número de factura")
        else:
            self.numero_input.setPlaceholderText("Número consecutivo del documento")

    def _cargar_documentos(self) -> None:
        docs = ProductoService.listar_documentos()
        self.table.setRowCount(len(docs))
        for row, d in enumerate(docs):
            self.table.setItem(row, 0, QTableWidgetItem(str(d.id)))
            self.table.setItem(row, 1, QTableWidgetItem(d.numero_documento or ""))
            self.table.setItem(row, 2, QTableWidgetItem(d.tipo or ""))
            self.table.setItem(
                row, 3,
                QTableWidgetItem(d.fecha.strftime("%Y-%m-%d") if d.fecha else ""),
            )
            self.table.setItem(row, 4, QTableWidgetItem(d.observaciones or ""))

    def _guardar(self) -> None:
        numero = self.numero_input.text().strip()
        tipo = self.tipo_combo.currentData()
        if not numero:
            QMessageBox.warning(self, "Validación", "El número del documento es obligatorio")
            return
        ok, res = ProductoService.crear_documento(
            numero_documento=numero,
            tipo=tipo,
            fecha=self.fecha_input.date().toPython(),
            observaciones=self.obs_input.text().strip() or None,
        )
        if ok:
            QMessageBox.information(self, "Éxito", f"Documento '{numero}' guardado")
            self.numero_input.clear()
            self.obs_input.clear()
            self._cargar_documentos()
        else:
            QMessageBox.warning(self, "Error", str(res))