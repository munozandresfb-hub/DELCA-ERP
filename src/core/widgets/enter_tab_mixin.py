"""Enter = Tab en formularios (mixin reutilizable).

Al presionar Enter en un campo, el foco salta a la siguiente sección del
formulario (igual que Tab). Si el foco está en un botón, Enter lo activa.
Enter nunca cierra el formulario por accidente.

Uso:
    class MiFormulario(EnterTabMixin, QDialog):
        def __init__(self, ...):
            super().__init__(...)
            ...
            self.installEventFilter(self)
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QPushButton, QWidget


class EnterTabMixin:
    """Provee el eventFilter Enter=Tab. Heredar junto a QDialog y llamar
    ``self.install_enter_tab()`` en __init__."""

    def install_enter_tab(self) -> None:
        """Instala el filtro a nivel de aplicación (captura los eventos de
        TODOS los widgets del formulario: campos y botones)."""
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if (
            event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            # Solo procesar eventos de este diálogo o de sus widgets hijos
            if not (
                obj is self
                or (isinstance(obj, QWidget) and self.isAncestorOf(obj))
            ):
                return super().eventFilter(obj, event)
            focus = QApplication.focusWidget()
            # Robustez: si el evento llega desde un botón (o el foco no está
            # disponible, p.ej. ventana sin activar), se toma el botón.
            if not isinstance(focus, QPushButton) and isinstance(obj, QPushButton):
                focus = obj
            if isinstance(focus, QPushButton):
                # Enter activa el botón con foco (⚡ Cambio Rápido / acción).
                # Los botones usan setAutoDefault(False) para que Enter en un
                # campo no los dispare; aquí se activan explícitamente.
                focus.click()
                return True
            self.focusNextChild()
            return True  # consumido: no cierra ni activa botones por defecto
        return super().eventFilter(obj, event)