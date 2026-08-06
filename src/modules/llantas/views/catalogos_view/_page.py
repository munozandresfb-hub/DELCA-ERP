from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from src.modules.llantas.views.catalogos_view._dialog import CatalogoMaestroDialog


class CatalogosPage(QWidget):
    """Sidebar page wrapper that opens CatalogoMaestroDialog."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        title = QLabel("Catálogos Maestros")
        title.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #2c3e50;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel(
            "Gestione marcas, dimensiones, diseños de banda\n"
            "y causas de rechazo desde un solo lugar."
        )
        desc.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        btn = QPushButton("Abrir Catálogos Maestros")
        btn.setStyleSheet(
            "QPushButton {"
            "  background: #3498db; color: white;"
            "  padding: 14px 40px; font-size: 16px;"
            "  border-radius: 8px; font-weight: bold;"
            "}"
            "QPushButton:hover { background: #2980b9; }"
        )
        btn.clicked.connect(self._abrir)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _abrir(self) -> None:
        dlg = CatalogoMaestroDialog(self)
        dlg.exec()