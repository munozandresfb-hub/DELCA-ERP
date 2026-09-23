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

    def __init__(
        self,
        tipo: str,
        parent: QWidget | None = None,
        numero_documento_inicial: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._tipo = tipo
        self._es_salida_ajuste = tipo in ("SALIDA", "AJUSTE")
        self._numero_guardado: str | None = None
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
            layout.addRow("Costo por KG $:", self.costo_input)

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

        # Mantener el número del documento anterior (constante hasta cambiarlo)
        if numero_documento_inicial and self._tipo in ("ENTRADA", "SALIDA"):
            self.doc_input.setText(numero_documento_inicial)

        # Observations
        self.obs_input = QLineEdit()
        self.obs_input.setPlaceholderText("Observaciones opcionales")
        layout.addRow("Observaciones:", self.obs_input)

        # Buttons: Ingresar producto (continúa sin cerrar) / Finalizar (cierra) / Cancelar
        btn_row = QHBoxLayout()
        btn_ingresar = QPushButton("📦 Ingresar producto")
        btn_ingresar.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_ingresar.clicked.connect(self._guardar_y_continuar)
        btn_row.addWidget(btn_ingresar)

        btn_finalizar = QPushButton("✅ Finalizar")
        btn_finalizar.setStyleSheet(
            "QPushButton { background: #2c3e50; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_finalizar.clicked.connect(self._guardar_y_finalizar)
        btn_row.addWidget(btn_finalizar)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancelar)
        layout.addRow(btn_row)

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
        for p in ProductoService.listar_productos(categoria="CONSUMIBLE", solo_activos=True):
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

    def _guardar_y_continuar(self) -> None:
        """Guarda el movimiento y limpia el formulario para agregar otro producto
        (el N° de documento permanece constante)."""
        if self._procesar():
            self.cantidad_input.clear()
            self.kg_input.clear()
            self.obs_input.clear()
            self.cantidad_input.setFocus()

    def _guardar_y_finalizar(self) -> None:
        """Guarda el movimiento y cierra el formulario."""
        if self._procesar():
            self.accept()

    def _procesar(self) -> bool:
        """Valida y registra el movimiento. Devuelve True si se registró."""
        data = self.producto_combo.currentData()
        if data is None:
            QMessageBox.warning(self, "Validación", "Seleccione un producto")
            return False
        producto_id, costo_default, unidad, _, _ = data

        try:
            cantidad = Decimal(self.cantidad_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad Und inválida")
            return False
        if cantidad < 0:
            QMessageBox.warning(self, "Validación", "La cantidad Und no puede ser negativa")
            return False
        if cantidad == 0 and self._tipo != "AJUSTE":
            QMessageBox.warning(self, "Validación", "La cantidad Und debe ser mayor a cero")
            return False

        try:
            cantidad_kg = Decimal(self.kg_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidad KG inválida")
            return False
        if cantidad_kg < 0:
            QMessageBox.warning(self, "Validación", "La cantidad KG no puede ser negativa")
            return False

        # Costo: editable solo en ENTRADA; en SALIDA/AJUSTE se usa el del producto
        if self.costo_input is not None:
            try:
                costo = Decimal(self.costo_input.text() or "0")
            except Exception:
                QMessageBox.warning(self, "Validación", "Costo inválido")
                return False
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
                return False
            ok, res = ProductoService.crear_documento(
                numero_documento=numero,
                tipo="INGRESO" if self._tipo == "ENTRADA" else "SALIDA",
                observaciones=self.obs_input.text().strip() or None,
            )
            if not ok:
                QMessageBox.warning(self, "Error", str(res))
                return False
            documento_id = int(res)
            self._numero_guardado = numero

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
        if not ok:
            QMessageBox.warning(self, "Error", str(msg))
            return False
        return True

    @property
    def numero_guardado(self) -> str | None:
        """Número de factura/documento usado en este movimiento (para recordarlo)."""
        return self._numero_guardado


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
        self.table.cellDoubleClicked.connect(self._ver_documento)
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

    def _ver_documento(self, row: int) -> None:
        """Doble clic sobre un número de documento -> detalle de sus movimientos."""
        item = self.table.item(row, 0)
        if item is None:
            return
        doc_id = int(item.text())
        numero = self.table.item(row, 1).text() if self.table.item(row, 1) else ""
        tipo = self.table.item(row, 2).text() if self.table.item(row, 2) else ""
        dlg = _DetalleDocumentoDialog(doc_id, numero, tipo, self)
        dlg.exec()


class _DetalleDocumentoDialog(QDialog):
    """Muestra la información que almacena un documento (productos, cantidades, fechas)."""

    def __init__(
        self,
        documento_id: int,
        numero_documento: str,
        tipo: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Documento {numero_documento}")
        self.resize(720, 400)
        self._documento_id = documento_id
        layout = QVBoxLayout()

        header = QLabel(
            f"<b>Documento:</b> {numero_documento} &nbsp;|&nbsp; "
            f"<b>Tipo:</b> {tipo} &nbsp;|&nbsp; <b>Movimientos:</b>"
        )
        layout.addWidget(header)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Producto", "SKU", "Tipo", "Cant. Und", "Cant. KG", "Referencia", "Observaciones"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.accept)

        btn_editar = QPushButton("✏️ Editar")
        btn_editar.setStyleSheet(
            "QPushButton { background: #2c3e50; color: white; font-weight: bold; "
            "padding: 8px 18px; border-radius: 5px; border: none; }"
        )
        btn_editar.clicked.connect(self._editar_seleccionado)

        btn_row = QHBoxLayout()
        btn_row.addWidget(btn_editar)
        btn_row.addStretch()
        btn_row.addWidget(btn_cerrar)
        layout.addLayout(btn_row)

        self.setLayout(layout)
        self._cargar(documento_id)

    def _cargar(self, documento_id: int) -> None:
        self._movs = ProductoService.movimientos_por_documento(documento_id)
        self.table.setRowCount(len(self._movs))
        for row, m in enumerate(self._movs):
            self.table.setItem(
                row, 0,
                QTableWidgetItem(m["fecha"].strftime("%Y-%m-%d %H:%M") if m["fecha"] else ""),
            )
            self.table.setItem(row, 1, QTableWidgetItem(m["producto"] or ""))
            self.table.setItem(row, 2, QTableWidgetItem(m["sku"] or ""))
            self.table.setItem(row, 3, QTableWidgetItem(m["tipo"] or ""))
            self.table.setItem(row, 4, QTableWidgetItem(f"{m['cantidad']:,.2f}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"{m['cantidad_kg']:,.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(m["referencia"] or ""))
            self.table.setItem(row, 7, QTableWidgetItem(m["observaciones"] or ""))

    def _editar_seleccionado(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._movs):
            QMessageBox.warning(self, "Validación", "Seleccione un producto del documento")
            return
        mov = self._movs[row]
        dlg = _EditarMovimientoDialog(mov, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cargar(self._documento_id)


class _EditarMovimientoDialog(QDialog):
    """Permite editar o eliminar un producto (movimiento) dentro de un documento."""

    def __init__(self, mov: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mov = mov
        self.setWindowTitle(f"Editar producto del documento — {mov.get('sku', '')}")
        self.resize(420, 300)
        layout = QFormLayout()

        # Producto (solo lectura)
        producto_lbl = QLabel(f"{mov.get('producto', '')} ({mov.get('sku', '')})")
        layout.addRow("Producto:", producto_lbl)

        tipo_lbl = QLabel(mov.get("tipo", ""))
        layout.addRow("Tipo:", tipo_lbl)

        self.cantidad_input = QLineEdit(str(mov.get("cantidad", 0)))
        layout.addRow("Cantidad Und:", self.cantidad_input)

        self.kg_input = QLineEdit(str(mov.get("cantidad_kg", 0)))
        layout.addRow("Cantidad KG:", self.kg_input)

        self.fecha_input = QDateEdit()
        self.fecha_input.setCalendarPopup(True)
        if mov.get("fecha"):
            self.fecha_input.setDate(
                QDate(mov["fecha"].year, mov["fecha"].month, mov["fecha"].day)
            )
        layout.addRow("Fecha:", self.fecha_input)

        self.obs_input = QLineEdit(mov.get("observaciones") or "")
        layout.addRow("Observaciones:", self.obs_input)

        # Botones
        btn_row = QHBoxLayout()
        btn_guardar = QPushButton("💾 Guardar cambios")
        btn_guardar.setStyleSheet(
            "QPushButton { background: #2e7d32; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_guardar.clicked.connect(self._guardar)
        btn_row.addWidget(btn_guardar)

        btn_eliminar = QPushButton("🗑️ Eliminar producto")
        btn_eliminar.setStyleSheet(
            "QPushButton { background: #c0392b; color: white; font-weight: bold; "
            "padding: 8px 16px; border-radius: 5px; border: none; }"
        )
        btn_eliminar.clicked.connect(self._eliminar)
        btn_row.addWidget(btn_eliminar)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancelar)
        layout.addRow(btn_row)

        self.setLayout(layout)

        # Un ajuste no se puede eliminar (el stock quedó fijado)
        if mov.get("tipo") == "AJUSTE":
            btn_eliminar.setEnabled(False)
            btn_eliminar.setToolTip("No se puede eliminar un ajuste (el stock quedó fijado)")

    def _guardar(self) -> None:
        try:
            cantidad = Decimal(self.cantidad_input.text() or "0")
            cantidad_kg = Decimal(self.kg_input.text() or "0")
        except Exception:
            QMessageBox.warning(self, "Validación", "Cantidades inválidas")
            return
        ok, msg = ProductoService.editar_movimiento(
            movimiento_id=self._mov["id"],
            cantidad=cantidad,
            cantidad_kg=cantidad_kg,
            fecha=self.fecha_input.date().toPython(),
            observaciones=self.obs_input.text().strip() or None,
        )
        if ok:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", str(msg))

    def _eliminar(self) -> None:
        resp = QMessageBox.question(
            self, "Eliminar producto",
            "¿Eliminar este producto del documento? El stock se revertirá.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return
        ok, msg = ProductoService.eliminar_movimiento(self._mov["id"])
        if ok:
            QMessageBox.information(self, "Éxito", str(msg))
            self.accept()
        else:
            QMessageBox.warning(self, "Error", str(msg))