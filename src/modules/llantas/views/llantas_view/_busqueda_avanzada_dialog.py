"""Diálogo de Búsqueda Avanzada del módulo Llantas.

Permite filtrar las llantas combinando varios criterios a la vez (AND):
cliente, dimensión, diseño, estado y ubicación.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.modules.clientes.services.cliente_service import ClienteService
from src.modules.llantas.services.llanta_service import (
    ESTADOS_PROCESO,
    UBICACIONES_DISPLAY,
    UBICACIONES_PLANTA,
    LlantaService,
)


class BusquedaAvanzadaDialog(QDialog):
    """Filtros combinables de llantas (cliente, dimensión, diseño, estado, ubicación)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Búsqueda Avanzada de Llantas")
        self.resize(420, 280)
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        form = QFormLayout()
        estilo = "font-size: 14px; padding: 4px; border: 1px solid #ccc; border-radius: 4px;"

        info = QLabel("Filtre con uno o varios criterios (se combinan):")
        info.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        layout.addWidget(info)

        # Cliente
        self.cliente_combo = QComboBox()
        self.cliente_combo.setStyleSheet(estilo)
        self.cliente_combo.addItem("Todos los clientes", None)
        for c in ClienteService.listar_clientes():
            if c.activo:
                self.cliente_combo.addItem(f"{c.nombre} ({c.nit})", c.id)
        form.addRow("Cliente:", self.cliente_combo)

        # Dimensión
        self.dimension_combo = QComboBox()
        self.dimension_combo.setStyleSheet(estilo)
        self.dimension_combo.addItem("Todas las dimensiones", None)
        for d in LlantaService.listar_dimensiones():
            self.dimension_combo.addItem(d.display, d.id)
        form.addRow("Dimensión:", self.dimension_combo)

        # Diseño
        self.diseno_combo = QComboBox()
        self.diseno_combo.setStyleSheet(estilo)
        self.diseno_combo.addItem("Todos los diseños", None)
        for d in LlantaService.listar_disenos():
            self.diseno_combo.addItem(d.nombre, d.id)
        form.addRow("Diseño:", self.diseno_combo)

        # Estado
        self.estado_combo = QComboBox()
        self.estado_combo.setStyleSheet(estilo)
        self.estado_combo.addItem("Todos los estados", None)
        for est in ESTADOS_PROCESO:
            self.estado_combo.addItem(est, est)
        form.addRow("Estado:", self.estado_combo)

        # Ubicación
        self.ubicacion_combo = QComboBox()
        self.ubicacion_combo.setStyleSheet(estilo)
        self.ubicacion_combo.addItem("Todas las ubicaciones", None)
        for u in UBICACIONES_PLANTA:
            self.ubicacion_combo.addItem(UBICACIONES_DISPLAY.get(u, u), u)
        form.addRow("Ubicación:", self.ubicacion_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        buscar_btn = QPushButton("🔍 Buscar")
        buscar_btn.setStyleSheet(
            "QPushButton { background-color: #3498db; color: white; font-size: 14px; "
            "font-weight: bold; padding: 8px 20px; border-radius: 5px; border: none; }"
        )
        buscar_btn.clicked.connect(self.accept)
        limpiar_btn = QPushButton("Limpiar")
        limpiar_btn.clicked.connect(self._limpiar)
        cancelar_btn = QPushButton("Cancelar")
        cancelar_btn.clicked.connect(self.reject)
        btn_layout.addWidget(buscar_btn)
        btn_layout.addWidget(limpiar_btn)
        btn_layout.addWidget(cancelar_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _limpiar(self) -> None:
        """Restablece todos los criterios a 'Todos'."""
        for combo in (
            self.cliente_combo,
            self.dimension_combo,
            self.diseno_combo,
            self.estado_combo,
            self.ubicacion_combo,
        ):
            combo.setCurrentIndex(0)

    def get_criterios(self) -> dict:
        """Devuelve los criterios seleccionados (None = sin filtro)."""
        return {
            "cliente_id": self.cliente_combo.currentData(),
            "dimension_id": self.dimension_combo.currentData(),
            "diseno_id": self.diseno_combo.currentData(),
            "estado": self.estado_combo.currentData(),
            "ubicacion": self.ubicacion_combo.currentData(),
        }