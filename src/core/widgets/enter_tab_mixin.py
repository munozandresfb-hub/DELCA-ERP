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
from PySide6.QtWidgets import QApplication, QPushButton


class EnterTabMixin:
    """Provee el eventFilter Enter=Tab. Heredar junto a QDialog."""

    def eventFilter(self, obj, event) -> bool:
        if (
            event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            if isinstance(QApplication.focusWidget(), QPushButton):
                return False  # Enter activa el botón con foco (acción / cerrar)
            self.focusNextChild()
            return True  # consumido: no cierra ni activa botones por defecto
        return super().eventFilter(obj, event)