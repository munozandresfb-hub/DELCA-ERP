import json

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.modules.automatizacion.forms.rule_form_dialog import RuleFormDialog
from src.modules.automatizacion.services.automatizacion_service import (
    AutomatizacionService,
)
from src.modules.automatizacion.views.automatizacion_view._constantes import (
    COLOR_BG_PRIMARY,
    COLOR_BORDER,
    COLOR_BG_CARD,
    COLOR_CRITICAL,
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_TEXT_SECONDARY,
    NIVEL_BG,
    NIVEL_COLORS,
)


class AutomatizacionView(QWidget):
    """Automation module: alerts, rules config, history."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.service = AutomatizacionService()
        self._setup_ui()
        self._load_data()
        self._start_auto_refresh()

    # ── UI setup ──────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── Header ──
        header = QLabel("⚙️ Automatización")
        header.setStyleSheet(
            f"""
            font-size: 22px;
            font-weight: bold;
            color: {COLOR_BG_PRIMARY};
            padding: 8px 0;
        """
        )
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
                background: white;
                padding: 12px;
            }}
            QTabBar::tab {{
                padding: 8px 20px;
                font-size: 13px;
                border: 1px solid transparent;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background: white;
                border-color: {COLOR_BORDER};
                font-weight: bold;
                color: {COLOR_BG_PRIMARY};
            }}
            QTabBar::tab:!selected {{
                background: #f5f6fa;
                color: {COLOR_TEXT_SECONDARY};
            }}
        """
        )

        self.tabs.addTab(self._build_alerts_tab(), "Alertas Activas")
        self.tabs.addTab(self._build_config_tab(), "Configuración")
        self.tabs.addTab(self._build_history_tab(), "Historial")

        layout.addWidget(self.tabs)

    # ── Tab 1: Alertas activas ────────────────────────────────

    def _build_alerts_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        self.lbl_no_leidas = QLabel("No leídas: 0")
        self.lbl_no_leidas.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {COLOR_BG_PRIMARY};"
        )
        toolbar.addWidget(self.lbl_no_leidas)
        toolbar.addStretch()

        btn_evaluar = QPushButton("🔍 Evaluar Reglas")
        btn_evaluar.setStyleSheet(self._btn_style(COLOR_BG_PRIMARY))
        btn_evaluar.clicked.connect(self._evaluar_reglas)
        toolbar.addWidget(btn_evaluar)

        btn_marcar_todas = QPushButton("✓ Marcar Todas Leídas")
        btn_marcar_todas.setStyleSheet(self._btn_style(COLOR_INFO))
        btn_marcar_todas.clicked.connect(self._marcar_todas_leidas)
        toolbar.addWidget(btn_marcar_todas)

        layout.addLayout(toolbar)

        # Table
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(5)
        self.alerts_table.setHorizontalHeaderLabels(
            ["Nivel", "Tipo", "Mensaje", "Fecha", "Acción"]
        )
        self.alerts_table.horizontalHeader().setStretchLastSection(False)
        self.alerts_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.alerts_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.alerts_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.verticalHeader().setVisible(False)
        self.alerts_table.setStyleSheet(self._table_style())
        layout.addWidget(self.alerts_table)

        return tab

    def _build_config_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        header = QLabel(
            "Reglas de automatización. Actívelas para que el sistema evalúe "
            "automáticamente y genere alertas."
        )
        header.setWordWrap(True)
        header.setStyleSheet(
            f"font-size: 13px; color: {COLOR_TEXT_SECONDARY}; padding-bottom: 8px;"
        )
        layout.addWidget(header)

        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(6)
        self.rules_table.setHorizontalHeaderLabels(
            ["ID", "Nombre", "Tipo", "Nivel", "Activa", "Acción"]
        )
        self.rules_table.horizontalHeader().setStretchLastSection(False)
        self.rules_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.rules_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.rules_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.rules_table.setAlternatingRowColors(True)
        self.rules_table.verticalHeader().setVisible(False)
        self.rules_table.setStyleSheet(self._table_style())
        layout.addWidget(self.rules_table)

        toolbar_config = QHBoxLayout()

        btn_nueva = QPushButton("➕ Nueva Regla")
        btn_nueva.setStyleSheet(self._btn_style(COLOR_SUCCESS))
        btn_nueva.clicked.connect(self._nueva_regla)
        toolbar_config.addWidget(btn_nueva)

        btn_refresh = QPushButton("🔄 Recargar")
        btn_refresh.setStyleSheet(
            self._btn_style(COLOR_BG_PRIMARY)
        )
        btn_refresh.clicked.connect(self._cargar_reglas)
        toolbar_config.addWidget(btn_refresh)

        toolbar_config.addStretch()
        layout.addLayout(toolbar_config)

        return tab

    def _build_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(
            ["Nivel", "Tipo", "Mensaje", "Entidad", "Leída", "Fecha"]
        )
        self.history_table.horizontalHeader().setStretchLastSection(
            False
        )
        self.history_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.history_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.history_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.history_table.setAlternatingRowColors(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setStyleSheet(self._table_style())
        layout.addWidget(self.history_table)

        btn_limpiar = QPushButton("🗑️ Limpiar Antiguas (+30 días)")
        btn_limpiar.setStyleSheet(
            self._btn_style(COLOR_TEXT_SECONDARY)
        )
        btn_limpiar.clicked.connect(self._limpiar_alertas)
        layout.addWidget(btn_limpiar, alignment=Qt.AlignLeft)

        return tab

    # ── Data loading ──────────────────────────────────────────

    def _load_data(self) -> None:
        self._cargar_alertas()
        self._cargar_reglas()
        self._cargar_historial()

    def _cargar_alertas(self) -> None:
        alertas = self.service.listar_alertas(solo_no_leidas=True)
        self.lbl_no_leidas.setText(
            f"No leídas: {len(alertas)}"
        )
        self.alerts_table.setRowCount(len(alertas))

        for i, a in enumerate(alertas):
            # Nivel badge
            nivel_item = QTableWidgetItem(a.nivel)
            color = NIVEL_COLORS.get(a.nivel, COLOR_INFO)
            bg = NIVEL_BG.get(a.nivel, "#fff")
            nivel_item.setBackground(QColor(bg))
            nivel_item.setForeground(QColor(color))
            nivel_item.setTextAlignment(Qt.AlignCenter)
            nivel_item.setFlags(Qt.ItemIsEnabled)
            self.alerts_table.setItem(i, 0, nivel_item)

            tipo_item = QTableWidgetItem(a.tipo)
            tipo_item.setFlags(Qt.ItemIsEnabled)
            self.alerts_table.setItem(i, 1, tipo_item)

            msg_item = QTableWidgetItem(a.mensaje)
            msg_item.setFlags(Qt.ItemIsEnabled)
            self.alerts_table.setItem(i, 2, msg_item)

            fecha_str = a.created_at.strftime(
                "%d/%m/%Y %H:%M"
            ) if a.created_at else ""
            fecha_item = QTableWidgetItem(fecha_str)
            fecha_item.setFlags(Qt.ItemIsEnabled)
            self.alerts_table.setItem(i, 3, fecha_item)

            # Action button
            btn_leer = QPushButton("✓ Leída")
            btn_leer.setStyleSheet(self._btn_style(COLOR_SUCCESS))
            alerta_id = a.id
            btn_leer.clicked.connect(
                lambda checked, aid=alerta_id: self._marcar_leida(aid)
            )
            self.alerts_table.setCellWidget(i, 4, btn_leer)

    def _cargar_reglas(self) -> None:
        reglas = self.service.listar_reglas()
        self.rules_table.setRowCount(len(reglas))

        for i, r in enumerate(reglas):
            id_item = QTableWidgetItem(str(r.id))
            id_item.setFlags(Qt.ItemIsEnabled)
            self.rules_table.setItem(i, 0, id_item)

            nombre_item = QTableWidgetItem(r.nombre)
            nombre_item.setFlags(Qt.ItemIsEnabled)
            self.rules_table.setItem(i, 1, nombre_item)

            tipo_item = QTableWidgetItem(r.tipo)
            tipo_item.setFlags(Qt.ItemIsEnabled)
            self.rules_table.setItem(i, 2, tipo_item)

            nivel_item = QTableWidgetItem(r.nivel)
            color = NIVEL_COLORS.get(r.nivel, COLOR_INFO)
            bg = NIVEL_BG.get(r.nivel, "#fff")
            nivel_item.setBackground(QColor(bg))
            nivel_item.setForeground(QColor(color))
            nivel_item.setTextAlignment(Qt.AlignCenter)
            nivel_item.setFlags(Qt.ItemIsEnabled)
            self.rules_table.setItem(i, 3, nivel_item)

            # Toggle button
            estado = "✅ Activa" if r.activa else "⛔ Inactiva"
            btn_toggle = QPushButton(estado)
            btn_toggle.setStyleSheet(
                self._btn_style(
                    COLOR_SUCCESS if r.activa else COLOR_TEXT_SECONDARY
                )
            )
            regla_id = r.id
            btn_toggle.clicked.connect(
                lambda checked, rid=regla_id: self._toggle_regla(rid)
            )
            self.rules_table.setCellWidget(i, 4, btn_toggle)

            # Action buttons: Editar / Eliminar
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)

            btn_editar = QPushButton("✏️")
            btn_editar.setToolTip("Editar regla")
            btn_editar.setFixedWidth(36)
            btn_editar.setStyleSheet(self._btn_style(COLOR_INFO))
            btn_editar.clicked.connect(
                lambda checked, rid=regla_id: self._editar_regla(rid)
            )
            action_layout.addWidget(btn_editar)

            btn_eliminar = QPushButton("🗑️")
            btn_eliminar.setToolTip("Eliminar regla")
            btn_eliminar.setFixedWidth(36)
            btn_eliminar.setStyleSheet(self._btn_style(COLOR_CRITICAL))
            btn_eliminar.clicked.connect(
                lambda checked, rid=regla_id: self._eliminar_regla(rid)
            )
            action_layout.addWidget(btn_eliminar)

            self.rules_table.setCellWidget(i, 5, action_widget)

    def _cargar_historial(self) -> None:
        alertas = self.service.listar_alertas(solo_no_leidas=False)
        self.history_table.setRowCount(len(alertas))

        for i, a in enumerate(alertas):
            nivel_item = QTableWidgetItem(a.nivel)
            color = NIVEL_COLORS.get(a.nivel, COLOR_INFO)
            bg = NIVEL_BG.get(a.nivel, "#fff")
            nivel_item.setBackground(QColor(bg))
            nivel_item.setForeground(QColor(color))
            nivel_item.setTextAlignment(Qt.AlignCenter)
            nivel_item.setFlags(Qt.ItemIsEnabled)
            self.history_table.setItem(i, 0, nivel_item)

            tipo_item = QTableWidgetItem(a.tipo)
            tipo_item.setFlags(Qt.ItemIsEnabled)
            self.history_table.setItem(i, 1, tipo_item)

            msg_item = QTableWidgetItem(a.mensaje)
            msg_item.setFlags(Qt.ItemIsEnabled)
            self.history_table.setItem(i, 2, msg_item)

            entidad = (
                f"{a.entidad_tipo}#{a.entidad_id}"
                if a.entidad_tipo and a.entidad_id
                else "—"
            )
            ent_item = QTableWidgetItem(entidad)
            ent_item.setFlags(Qt.ItemIsEnabled)
            self.history_table.setItem(i, 3, ent_item)

            leida_str = "✓ Sí" if a.leida else "✗ No"
            leida_item = QTableWidgetItem(leida_str)
            leida_item.setFlags(Qt.ItemIsEnabled)
            leida_item.setTextAlignment(Qt.AlignCenter)
            self.history_table.setItem(i, 4, leida_item)

            fecha_str = a.created_at.strftime(
                "%d/%m/%Y %H:%M"
            ) if a.created_at else ""
            fecha_item = QTableWidgetItem(fecha_str)
            fecha_item.setFlags(Qt.ItemIsEnabled)
            self.history_table.setItem(i, 5, fecha_item)

    # ── Actions ───────────────────────────────────────────────

    def _evaluar_reglas(self) -> None:
        count = self.service.evaluar_reglas()
        QMessageBox.information(
            self,
            "Evaluación completa",
            f"Se generaron {count} alerta(s).",
        )
        self._load_data()

    def _marcar_leida(self, alerta_id: int) -> None:
        self.service.marcar_leida(alerta_id)
        self._load_data()

    def _marcar_todas_leidas(self) -> None:
        self.service.marcar_todas_leidas()
        self._load_data()

    def _toggle_regla(self, regla_id: int) -> None:
        ok, msg = self.service.toggle_regla(regla_id)
        if not ok:
            QMessageBox.warning(self, "Error", msg)
        self._cargar_reglas()

    def _nueva_regla(self) -> None:
        dialog = RuleFormDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_form_data()
        config_dict = {}
        try:
            config_dict = json.loads(data["config_json"])
        except (json.JSONDecodeError, TypeError):
            config_dict = {}
        self.service.crear_regla(
            nombre=data["nombre"],
            tipo=data["tipo"],
            nivel=data["nivel"],
            activa=data["activa"],
            config_dict=config_dict,
        )
        self._cargar_reglas()

    def _editar_regla(self, regla_id: int) -> None:
        regla = self.service.obtener_regla(regla_id)
        if not regla:
            QMessageBox.warning(self, "Error", "Regla no encontrada.")
            return
        regla_data = {
            "id": regla.id,
            "nombre": regla.nombre,
            "tipo": regla.tipo,
            "nivel": regla.nivel,
            "activa": regla.activa,
            "config_json": regla.config_json,
        }
        dialog = RuleFormDialog(self, regla_data=regla_data)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_form_data()
        config_dict = {}
        try:
            config_dict = json.loads(data["config_json"])
        except (json.JSONDecodeError, TypeError):
            config_dict = {}
        ok, msg = self.service.actualizar_regla(
            regla_id=regla_id,
            nombre=data["nombre"],
            tipo=data["tipo"],
            nivel=data["nivel"],
            activa=data["activa"],
            config_dict=config_dict,
        )
        if not ok:
            QMessageBox.warning(self, "Error", msg)
        self._cargar_reglas()

    def _eliminar_regla(self, regla_id: int) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Eliminar la regla ID {regla_id}? Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        ok, msg = self.service.eliminar_regla(regla_id)
        if not ok:
            QMessageBox.warning(self, "Error", msg)
        self._cargar_reglas()

    def _limpiar_alertas(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar alertas con más de 30 días?",
        )
        if reply == QMessageBox.Yes:
            self.service.limpiar_alertas(dias=30)
            self._load_data()

    def _start_auto_refresh(self) -> None:
        """Auto-evaluate rules every 5 minutes."""
        timer = QTimer(self)
        timer.timeout.connect(self._auto_evaluate)
        timer.start(300_000)  # 5 min

    def _auto_evaluate(self) -> None:
        self.service.evaluar_reglas()
        self._load_data()

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _btn_style(base_color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {base_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
        """

    @staticmethod
    def _table_style() -> str:
        return f"""
            QTableWidget {{
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                background: {COLOR_BG_CARD};
                gridline-color: #eee;
                font-size: 13px;
            }}
            QHeaderView::section {{
                background-color: {COLOR_BG_PRIMARY};
                color: white;
                padding: 8px 12px;
                font-weight: bold;
                font-size: 12px;
                border: none;
            }}
            QTableWidget::item {{
                padding: 6px 8px;
            }}
            QTableWidget::item:selected {{
                background: #dfe6e9;
                color: {COLOR_BG_PRIMARY};
            }}
        """