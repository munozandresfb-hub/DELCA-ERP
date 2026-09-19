from collections.abc import Callable

from PySide6.QtCore import QTimer, QEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.core.views.dashboard_view import DashboardView
from src.modules.clientes.views.clientes_view import ClientesView
from src.modules.finanzas.views.cartera_view import CarteraView
from src.modules.finanzas.views.facturacion_view import FacturacionView
from src.modules.inventario.views.inventario_view import InventarioView
from src.modules.inventario.views.kardex_view import KardexView
from src.modules.automatizacion.views.automatizacion_view import (
    AutomatizacionView,
)
from src.modules.reportes.views.reportes_view import ReportesView
from src.modules.llantas.views.llantas_view import LlantasView
from src.modules.llantas.views.produccion_view import ProduccionView
from src.modules.llantas.views.planta_view import PlantaView
from src.modules.llantas.views.catalogos_view import CatalogosPage
from src.core.views.backup_view import BackupView
from src.modules.usuarios.views.usuarios_view import UsuariosView

# ─── Session tracking for inactivity timeout ─────────────────────────
from src.core.services.session_service import get_session_manager

# ─── Backup automático ───────────────────────────────────────────────
from src.core.services.backup_service import (
    create_backup,
    get_last_backup_time,
    was_backup_done_today,
)

# ─── RBAC ────────────────────────────────────────────────────────────
from src.modules.usuarios.services.permiso_service import tiene_permiso_por_usuario


class PlaceholderPage(QWidget):
    """Placeholder for unimplemented or errored pages."""

    def __init__(self, title: str, error: str = "") -> None:
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel(f"Módulo {title}")
        label.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 20px; color: #999;"
        )
        layout.addWidget(label)
        if error:
            err_lbl = QLabel(f"Error al cargar:\n{error}")
            err_lbl.setStyleSheet(
                "font-size: 13px; padding: 10px; color: #e74c3c; "
                "background: #fdf0ef; border-radius: 4px;"
            )
            err_lbl.setWordWrap(True)
            layout.addWidget(err_lbl)
        else:
            coming = QLabel("Próximamente...")
            coming.setStyleSheet("font-size: 14px; padding: 10px; color: #bbb;")
            layout.addWidget(coming)
        layout.addStretch()
        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""

    def __init__(self, user) -> None:
        super().__init__()

        self.user = user
        self._session = get_session_manager()
        self._session.set_user(user)

        self.setWindowTitle(f"DELCA ERP - {user.nombre}")
        self.resize(1200, 700)

        self.setup_ui()
        self._setup_inactivity_timer()
        self._setup_backup_scheduler()
        self._setup_status_bar()

    def setup_ui(self) -> None:
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout()

        # =========================
        # SIDEBAR — filtered by RBAC
        # =========================
        # (label, permission_codigo, view_factory)
        self._sidebar_items: list[tuple[str, str, Callable]] = [
            ("Dashboard", "dashboard.ver", lambda: DashboardView(self.user)),
            ("Clientes", "clientes.ver", lambda: ClientesView(self.user)),
            ("Llantas", "llantas.ver", lambda: LlantasView()),
            ("Producción", "produccion.ver", lambda: ProduccionView()),
            ("Planta", "planta.ver", lambda: PlantaView()),
            ("Catálogos", "llantas.ver", lambda: CatalogosPage()),
            ("Facturación", "facturacion.ver", lambda: FacturacionView()),
            ("Cartera", "cartera.ver", lambda: CarteraView(self.user)),
            ("Inventario", "inventario.ver", lambda: InventarioView()),
            ("Kardex", "kardex.ver", lambda: KardexView()),
            ("Reportes", "reportes.ver", lambda: ReportesView()),
            ("Automatización", "automatizacion.ver", lambda: AutomatizacionView()),
            ("Usuarios", "usuarios.gestionar", lambda: UsuariosView(self.user)),
            ("Backup", "backup.gestionar", lambda: BackupView()),
        ]

        # Filter by user permissions
        self.sidebar = QListWidget()
        self._visible_indices: list[int] = []
        for idx, (label, perm, factory) in enumerate(self._sidebar_items):
            if tiene_permiso_por_usuario(self.user, perm):
                self._visible_indices.append(idx)
                self.sidebar.addItem(label)
        self.sidebar.setMaximumWidth(200)
        self.sidebar.setMinimumWidth(180)
        self.sidebar.setStyleSheet(
            """
            QListWidget {
                background-color: #2c3e50;
                color: white;
                font-size: 14px;
                padding: 10px;
                border: none;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background-color: #3498db;
            }
            QListWidget::item:hover {
                background-color: #34495e;
            }
            """
        )

        self.sidebar.currentRowChanged.connect(self.change_page)

        # =========================
        # STACK — only authorized pages (carga LAZY: la vista se instancia
        # al hacer clic en el sidebar, no al entrar — login rápido)
        # =========================
        self.stack = QStackedWidget()
        self._idx_to_widget: dict[int, QWidget | None] = {
            real_idx: None for real_idx in self._visible_indices
        }

        # Initial selection (dispara change_page -> carga el Dashboard)
        self.sidebar.setCurrentRow(0)

        # Add to layout
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        central_widget.setLayout(main_layout)

    def change_page(self, visible_index: int) -> None:
        """Map the visible sidebar row to the actual backend page."""
        if 0 <= visible_index < len(self._visible_indices):
            real_idx = self._visible_indices[visible_index]
            widget = self._obtener_widget(real_idx)
            if widget:
                self.stack.setCurrentWidget(widget)
                self._recargar_vista(widget)

    def _obtener_widget(self, real_idx: int) -> QWidget | None:
        """Instancia la vista bajo demanda (lazy) y la cachea en el stack."""
        widget = self._idx_to_widget.get(real_idx)
        if widget is None:
            label, perm, factory = self._sidebar_items[real_idx]
            try:
                widget = factory()
            except Exception as e:
                print(f"[MainWindow] Error cargando '{label}': {e}")
                widget = PlaceholderPage(label, str(e))
            self._idx_to_widget[real_idx] = widget
            self.stack.addWidget(widget)
        return widget

    def _recargar_vista(self, widget: QWidget) -> None:
        """Recarga los datos de la vista entrante para reflejar cambios
        hechos desde otros módulos sin pulsar 'Actualizar'."""
        for nombre in (
            "_cargar_datos",
            "_refresh_all",
            "_load_data",
            "_refresh_backup_list",
        ):
            metodo = getattr(widget, nombre, None)
            if callable(metodo):
                try:
                    metodo()
                except Exception as e:
                    print(
                        f"[MainWindow] Error recargando '{type(widget).__name__}': {e}"
                    )
                return

    # ── Inactivity timeout ────────────────────────────────────────────

    def _setup_inactivity_timer(self) -> None:
        """Check every 30s if session expired."""
        # Operador no tiene cierre por inactividad
        if hasattr(self.user, "rol") and self.user.rol.nombre == "Operador":
            return

        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.timeout.connect(self._check_inactivity)
        self._inactivity_timer.start(30_000)

        # Track user activity via event filter.
        # Instalado en la APLICACIÓN (no en centralWidget) para capturar también
        # la actividad dentro de diálogos modales (QMessageBox, QDialog), cuyos
        # eventos NO pasan por un filter del central widget.
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        # Also track on sidebar clicks
        self.sidebar.currentRowChanged.connect(
            lambda _: self._session.update_activity()
        )

    def eventFilter(self, obj, event) -> bool:
        """Reset inactivity timer on mouse/keyboard events (app-wide)."""
        if event.type() in (QEvent.MouseButtonPress, QEvent.KeyPress,
                            QEvent.MouseMove, QEvent.Wheel):
            self._session.update_activity()
        return super().eventFilter(obj, event)

    def _check_inactivity(self) -> None:
        """Lock UI if session expired."""
        if self._session.is_session_expired():
            self._session.lock()
            # Show a simple lock message
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Sesión Expirada")
            msg.setText(
                "Su sesión ha expirado por inactividad.\n"
                "Por favor, cierre y vuelva a iniciar sesión."
            )
            msg.exec()
            self.close()

    # ── Backup automático (Roadmap Fase 1) ────────────────────────────

    def _setup_backup_scheduler(self) -> None:
        """Backup automático diario.

        - Al arrancar la app (3s después), crea el backup del día si falta.
        - Timer cada 6h como red de seguridad (cubre el cambio de día con la
          app abierta: al pasar de medianoche, el siguiente tick detecta que
          ya no hay backup de hoy y lo crea).
        - Solo se informa al usuario si el backup FALLA (no molesta si todo OK).
        """
        self._backup_timer = QTimer(self)
        self._backup_timer.timeout.connect(self._check_auto_backup)
        self._backup_timer.start(6 * 60 * 60 * 1000)  # cada 6 horas

        # Backup del día al arrancar (no depende de abrir el módulo Backup)
        QTimer.singleShot(3_000, self._check_auto_backup)

    def _check_auto_backup(self) -> None:
        """Crea el backup del día si aún no existe. Informa solo si falla."""
        if was_backup_done_today():
            return
        ok, msg = create_backup()
        if ok:
            print(f"[Backup] Automático diario OK: {msg}")
            self._refresh_status_bar()
        else:
            print(f"[Backup] Automático falló: {msg}")
            self._notify_backup_failed(msg)

    def _notify_backup_failed(self, msg: str) -> None:
        """Avisa al usuario solo si el backup automático falló."""
        if not hasattr(self.user, "rol"):
            return
        try:
            if self.user.rol.nombre == "Operador":
                return
        except Exception:
            pass
        QTimer.singleShot(
            0,
            lambda: QMessageBox.warning(
                self,
                "Backup automático",
                f"No se pudo crear el respaldo de la base de datos:\n"
                f"{msg}\n\n"
                "Revise el módulo Backup para más detalles.",
            ),
        )

    # ── Barra de estado (Roadmap Fase 1) ──────────────────────────────

    def _setup_status_bar(self) -> None:
        """Barra de estado: usuario, rol y último backup."""
        status = QStatusBar()
        self.setStatusBar(status)

        rol = "—"
        try:
            if hasattr(self.user, "rol") and self.user.rol is not None:
                rol = self.user.rol.nombre
        except Exception:
            pass

        self._status_user = QLabel(f"👤 {self.user.nombre} · {rol}")
        self._status_backup = QLabel("")

        status.addWidget(self._status_user)
        status.addPermanentWidget(self._status_backup)
        self._refresh_status_bar()

    def _refresh_status_bar(self) -> None:
        ultimo = get_last_backup_time() or "nunca"
        self._status_backup.setText(f"💾 Último backup: {ultimo}")
