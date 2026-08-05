"""
Backup & Recovery management view for DELCA ERP.

Provides UI for: creating backups, listing/restoring backups,
CSV/Excel export, integrity verification, and recovery guidance.
"""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.core.services.backup_service import (
    ALL_TABLES,
    create_backup,
    export_all_tables,
    export_to_csv,
    export_to_excel,
    get_last_backup_time,
    list_backups,
    restore_backup,
    verify_integrity,
    was_backup_done_today,
)


class BackupView(QWidget):
    """Backup and recovery management interface (sidebar index 11)."""

    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self._refresh_backup_list()

        # Auto-backup check on startup
        QTimer.singleShot(5000, self._auto_backup_check)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🔄 Backup & Recuperación")
        title.setStyleSheet("font-size: 20px; font-weight: bold; padding: 10px 0;")
        layout.addWidget(title)

        # ── Tabs ───────────────────────────────────────────────────
        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._build_backup_tab(), "Backup / Restore")
        tabs.addTab(self._build_export_tab(), "Exportar Datos")
        tabs.addTab(self._build_recovery_tab(), "Recuperación")

        # ── Status bar ─────────────────────────────────────────────
        self.status_label = QLabel("Listo")
        self.status_label.setStyleSheet(
            "padding: 5px; color: #555; font-size: 12px;"
        )
        layout.addWidget(self.status_label)

        # Auto-refresh timer (every 60 seconds)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_backup_list)
        self._refresh_timer.start(60_000)

    # ==================================================================
    #  TAB 1: Backup / Restore
    # ==================================================================

    def _build_backup_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ── Create backup ──────────────────────────────────────────
        backup_group = QGroupBox("Crear Backup")
        blayout = QHBoxLayout(backup_group)

        self.btn_backup = QPushButton("📦 Crear Backup Ahora")
        self.btn_backup.setStyleSheet(
            "background-color: #27ae60; color: white; padding: 10px 20px;"
            " font-size: 14px; border-radius: 5px;"
        )
        self.btn_backup.clicked.connect(self._on_create_backup)
        blayout.addWidget(self.btn_backup)

        self.last_backup_label = QLabel("Último backup: --")
        self.last_backup_label.setStyleSheet("padding: 10px; color: #555;")
        blayout.addWidget(self.last_backup_label)
        blayout.addStretch()

        layout.addWidget(backup_group)

        # ── Backup list ────────────────────────────────────────────
        list_group = QGroupBox("Backups Disponibles")
        list_layout = QVBoxLayout(list_group)

        self.backup_table = QTableWidget()
        self.backup_table.setColumnCount(4)
        self.backup_table.setHorizontalHeaderLabels(
            ["Archivo", "Tamaño", "Fecha", "Acción"]
        )
        self.backup_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.backup_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.backup_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.backup_table.setAlternatingRowColors(True)
        self.backup_table.verticalHeader().setVisible(False)

        list_layout.addWidget(self.backup_table)
        layout.addWidget(list_group)

        return tab

    def _on_create_backup(self) -> None:
        self.status_label.setText("Creando backup...")
        ok, result = create_backup()
        if ok:
            self.status_label.setText(f"✅ Backup creado: {Path(result).name}")
            self._refresh_backup_list()
            self.last_backup_label.setText(
                f"Último backup: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            QMessageBox.critical(self, "Error", f"Backup falló: {result}")
            self.status_label.setText(f"❌ {result}")

    def _on_restore(self, backup_path: str) -> None:
        reply = QMessageBox.warning(
            self,
            "Confirmar Restauración",
            "¿Está seguro? La base de datos actual se renombrará a .bak\n"
            "y será reemplazada por el backup seleccionado.\n\n"
            "La aplicación debe reiniciarse después de la restauración.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.status_label.setText("Restaurando...")
        ok, msg = restore_backup(backup_path)
        if ok:
            QMessageBox.information(
                self,
                "Restauración Exitosa",
                f"{msg}\n\nReinicie la aplicación para usar la base restaurada.",
            )
            self.status_label.setText(f"✅ {msg}")
        else:
            QMessageBox.critical(self, "Error", msg)
            self.status_label.setText(f"❌ {msg}")
        self._refresh_backup_list()

    def _refresh_backup_list(self) -> None:
        backups = list_backups()
        self.backup_table.setRowCount(len(backups))

        for row, b in enumerate(backups):
            self.backup_table.setItem(row, 0, QTableWidgetItem(b["name"]))
            self.backup_table.setItem(row, 1, QTableWidgetItem(b["size_display"]))
            self.backup_table.setItem(row, 2, QTableWidgetItem(b["date"]))

            btn = QPushButton("Restaurar")
            btn.setStyleSheet(
                "background-color: #e67e22; color: white; padding: 4px 12px;"
                " border-radius: 3px;"
            )
            btn.clicked.connect(
                lambda checked=False, p=b["path"]: self._on_restore(p)
            )
            self.backup_table.setCellWidget(row, 3, btn)

        # Update last backup label
        last_time = get_last_backup_time()
        if last_time:
            self.last_backup_label.setText(f"Último backup: {last_time}")

    def _auto_backup_check(self) -> None:
        """Create a daily backup if none exists yet today."""
        if not was_backup_done_today():
            ok, result = create_backup()
            if ok:
                self.status_label.setText(
                    f"✅ Backup automático del día creado: {Path(result).name}"
                )
                self._refresh_backup_list()

    # ==================================================================
    #  TAB 2: Export
    # ==================================================================

    def _build_export_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # ── Table selector ─────────────────────────────────────────
        export_group = QGroupBox("Exportar Tabla Individual")
        egrid = QHBoxLayout(export_group)

        egrid.addWidget(QLabel("Tabla:"))

        self.table_combo = QComboBox()
        self.table_combo.addItems(ALL_TABLES)
        self.table_combo.setMinimumWidth(250)
        egrid.addWidget(self.table_combo)

        self.btn_export_csv = QPushButton("📄 Exportar CSV")
        self.btn_export_csv.clicked.connect(self._on_export_csv)
        egrid.addWidget(self.btn_export_csv)

        self.btn_export_xlsx = QPushButton("📊 Exportar Excel")
        self.btn_export_xlsx.clicked.connect(self._on_export_xlsx)
        egrid.addWidget(self.btn_export_xlsx)

        egrid.addStretch()
        layout.addWidget(export_group)

        # ── Export all ─────────────────────────────────────────────
        all_group = QGroupBox("Exportar Todo")
        alayout = QHBoxLayout(all_group)

        self.btn_export_all = QPushButton("📦 Exportar Todas las Tablas a CSV")
        self.btn_export_all.setStyleSheet(
            "background-color: #2980b9; color: white; padding: 8px 16px;"
            " border-radius: 4px;"
        )
        self.btn_export_all.clicked.connect(self._on_export_all)
        alayout.addWidget(self.btn_export_all)
        alayout.addStretch()

        layout.addWidget(all_group)
        layout.addStretch()

        return tab

    def _on_export_csv(self) -> None:
        table = self.table_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, f"Exportar {table} como CSV", f"{table}.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        ok, msg = export_to_csv(table, path)
        if ok:
            self.status_label.setText(f"✅ {msg}")
        else:
            QMessageBox.critical(self, "Error", msg)

    def _on_export_xlsx(self) -> None:
        table = self.table_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(
            self, f"Exportar {table} como Excel", f"{table}.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return
        ok, msg = export_to_excel(table, path)
        if ok:
            self.status_label.setText(f"✅ {msg}")
        else:
            QMessageBox.critical(self, "Error", msg)

    def _on_export_all(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Seleccionar carpeta para exportar"
        )
        if not directory:
            return
        results = export_all_tables(directory)
        if results:
            self.status_label.setText(
                f"✅ Exportadas {len(results)} tablas a {directory}"
            )
        else:
            QMessageBox.critical(self, "Error", "No se pudo exportar ninguna tabla")

    # ==================================================================
    #  TAB 3: Recovery Guide
    # ==================================================================

    def _build_recovery_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QTextBrowser()
        info.setOpenExternalLinks(True)
        info.setStyleSheet("font-size: 13px; padding: 15px;")
        info.setHtml(
            """
<h2>🛟 Recuperación ante Desastres</h2>
<p><b>Tiempo estimado de recuperación: &lt; 5 minutos</b></p>

<h3>Escenario: Base de datos corrupta o perdida</h3>
<ol>
<li><b>Verificar integridad</b> — Use el botón abajo para ejecutar
    <code>PRAGMA integrity_check</code>.</li>
<li><b>Restaurar desde backup</b> — Vaya a la pestaña "Backup / Restore",
    seleccione el backup más reciente y haga clic en "Restaurar".</li>
<li><b>Reiniciar</b> — Cierre y vuelva a abrir la aplicación.</li>
</ol>

<h3>Escenario: Sin backups disponibles</h3>
<ol>
<li><b>Revise la carpeta backups/</b> para archivos .db manuales.</li>
<li><b>Revise delca.db.bak</b> en la carpeta del proyecto
    (backup automático de seguridad).</li>
<li><b>Como último recurso</b>, inicie la aplicación desde cero
    (se creará una base de datos nueva vacía).</li>
</ol>

<h3>Recomendaciones</h3>
<ul>
<li>Realice backups diarios (el sistema lo hace automáticamente).</li>
<li>Exporte datos críticos (clientes, facturas) semanalmente a CSV.</li>
<li>Mantenga al menos 3 copias de backup en ubicaciones separadas.</li>
</ul>

<h3>Integridad de la Base de Datos Actual</h3>
"""
        )
        layout.addWidget(info)

        self.btn_verify = QPushButton("🔍 Verificar Integridad de la BD")
        self.btn_verify.setStyleSheet(
            "background-color: #8e44ad; color: white; padding: 10px 20px;"
            " font-size: 14px; border-radius: 5px;"
        )
        self.btn_verify.clicked.connect(self._on_verify_integrity)
        layout.addWidget(self.btn_verify)

        self.integrity_result = QLabel("")
        self.integrity_result.setStyleSheet("padding: 10px; font-size: 13px;")
        layout.addWidget(self.integrity_result)

        layout.addStretch()
        return tab

    def _on_verify_integrity(self) -> None:
        self.integrity_result.setText("Verificando...")
        ok, msg = verify_integrity()
        if ok:
            self.integrity_result.setStyleSheet(
                "padding: 10px; font-size: 13px; color: green;"
            )
            self.integrity_result.setText(f"✅ {msg}")
        else:
            self.integrity_result.setStyleSheet(
                "padding: 10px; font-size: 13px; color: red;"
            )
            self.integrity_result.setText(f"❌ {msg}")
