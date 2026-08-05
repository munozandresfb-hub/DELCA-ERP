from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class RuleFormDialog(QDialog):
    """Dialog for creating or editing an automation rule.

    Shows dynamic parameter fields based on the selected rule type.
    """

    TIPOS = [
        "STOCK_BAJO",
        "CARTERA_VENCIDA",
        "LLANTAS_LISTAS",
    ]

    NIVELES = ["INFO", "WARNING", "CRITICAL"]

    # Map tipo → list of (param_name, label, default)
    PARAMS_MAP: dict[str, list[tuple[str, str, int]]] = {
        "STOCK_BAJO": [("umbral", "Umbral mínimo (unidades)", 10)],
        "CARTERA_VENCIDA": [("dias", "Días de vencimiento", 30)],
        "LLANTAS_LISTAS": [],
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        regla_data: dict | None = None,
    ) -> None:
        """Create the dialog.

        Args:
            parent: Parent widget.
            regla_data: If provided, dialog opens in edit mode
                with fields pre-filled. Expects keys:
                id, nombre, tipo, nivel, activa, config_json.
        """
        super().__init__(parent)
        self._regla_data = regla_data
        self._editing = regla_data is not None
        self._param_spins: dict[str, QSpinBox] = {}

        self.setWindowTitle(
            "Editar Regla" if self._editing else "Nueva Regla"
        )
        self.setMinimumWidth(420)
        self._setup_ui()

        if self._editing:
            self._load_regla_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ── Basic fields ──
        form = QFormLayout()
        form.setSpacing(10)

        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ej: Stock Bajo")
        self.nombre_input.setMaxLength(100)
        form.addRow("Nombre:", self.nombre_input)

        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(self.TIPOS)
        self.tipo_combo.currentTextChanged.connect(self._on_tipo_changed)
        form.addRow("Tipo:", self.tipo_combo)

        self.nivel_combo = QComboBox()
        self.nivel_combo.addItems(self.NIVELES)
        form.addRow("Nivel:", self.nivel_combo)

        self.activa_check = QCheckBox("Regla activa al guardar")
        self.activa_check.setChecked(True)
        form.addRow(self.activa_check)

        layout.addLayout(form)

        # ── Dynamic params ──
        self.params_group = QGroupBox("Parámetros")
        self.params_layout = QFormLayout(self.params_group)
        self.params_layout.setSpacing(8)
        layout.addWidget(self.params_group)

        # Build initial param fields for default tipo
        self._rebuild_params(self.tipo_combo.currentText())

        # ── Buttons ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ── Dynamic params ───────────────────────────────────────

    def _on_tipo_changed(self, tipo: str) -> None:
        self._rebuild_params(tipo)

    def _rebuild_params(self, tipo: str) -> None:
        """Replace param fields for the given rule type."""
        # Clear existing
        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._param_spins.clear()

        params = self.PARAMS_MAP.get(tipo, [])
        if not params:
            label = QLabel(
                "Esta regla no requiere parámetros adicionales."
            )
            label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            self.params_layout.addRow(label)
            self.params_group.setVisible(True)
            return

        for param_name, label_text, default in params:
            spin = QSpinBox()
            spin.setMinimum(1)
            spin.setMaximum(999999)
            spin.setValue(default)
            spin.setSuffix(" días" if "dias" in param_name else " uds." if "umbral" in param_name else "")
            spin.setFixedWidth(140)
            self._param_spins[param_name] = spin
            self.params_layout.addRow(f"{label_text}:", spin)

        self.params_group.setVisible(True)

    # ── Load / Save ──────────────────────────────────────────

    def _load_regla_data(self) -> None:
        """Populate fields from existing rule data."""
        data = self._regla_data
        if not data:
            return

        self.nombre_input.setText(data.get("nombre", ""))
        tipo = data.get("tipo", "")
        idx = self.tipo_combo.findText(tipo)
        if idx >= 0:
            self.tipo_combo.setCurrentIndex(idx)

        nivel = data.get("nivel", "WARNING")
        idx = self.nivel_combo.findText(nivel)
        if idx >= 0:
            self.nivel_combo.setCurrentIndex(idx)

        self.activa_check.setChecked(data.get("activa", True))

        # Load config_json into param spins
        config_str = data.get("config_json") or "{}"
        try:
            config = json.loads(config_str)
        except (json.JSONDecodeError, TypeError):
            config = {}
        for param_name, spin in self._param_spins.items():
            if param_name in config:
                spin.setValue(int(config[param_name]))

    def get_form_data(self) -> dict:
        """Return form values as a dict."""
        config = {}
        for param_name, spin in self._param_spins.items():
            config[param_name] = spin.value()

        return {
            "nombre": self.nombre_input.text().strip(),
            "tipo": self.tipo_combo.currentText(),
            "nivel": self.nivel_combo.currentText(),
            "activa": self.activa_check.isChecked(),
            "config_json": json.dumps(config),
        }

    def _validate_and_accept(self) -> None:
        nombre = self.nombre_input.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            self.nombre_input.setFocus()
            return
        self.accept()
