from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)


class _MetricCard(QFrame):
    """Single metric card with title, value, and accent color."""

    def __init__(
        self, titulo: str, valor: str, color: str, icono: str = ""
    ) -> None:
        super().__init__()
        self.setStyleSheet(
            f"""
            _MetricCard {{
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e8ecf0;
            }}
            _MetricCard:hover {{
                border: 1px solid {color};
            }}
            """
        )
        self.setMinimumSize(180, 120)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)

        # Top row: icon + value
        top = QHBoxLayout()
        top.setSpacing(10)

        if icono:
            icon_label = QLabel(icono)
            icon_label.setStyleSheet("font-size: 22px;")
            top.addWidget(icon_label)

        value_label = QLabel(str(valor))
        value_label.setStyleSheet(
            f"font-size: 32px; font-weight: 700; color: {color};"
        )
        top.addWidget(value_label)
        top.addStretch()
        layout.addLayout(top)

        # Accent bar
        bar = QFrame()
        bar.setFixedHeight(3)
        bar.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        layout.addWidget(bar)

        # Title
        title_label = QLabel(titulo)
        title_label.setStyleSheet(
            "font-size: 13px; color: #7f8c8d; font-weight: 500;"
        )
        layout.addWidget(title_label)

        self.setLayout(layout)


class _EstadoCard(QFrame):
    """Colored card for an aggregated state metric."""

    def __init__(self, titulo: str, valor: str, color: str, icono: str, desc: str = "") -> None:
        super().__init__()
        self.setStyleSheet(
            f"""
            _EstadoCard {{
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e8ecf0;
                border-left: 4px solid {color};
            }}
            _EstadoCard:hover {{
                border-color: {color};
            }}
            """
        )
        self.setMinimumSize(180, 110)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        # Top: icon + value
        top = QHBoxLayout()
        top.setSpacing(8)
        if icono:
            icon_label = QLabel(icono)
            icon_label.setStyleSheet("font-size: 20px;")
            top.addWidget(icon_label)
        value_label = QLabel(str(valor))
        value_label.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {color};"
        )
        top.addWidget(value_label)
        top.addStretch()
        layout.addLayout(top)

        # Title
        title_label = QLabel(titulo)
        title_label.setStyleSheet(
            "font-size: 13px; color: #2c3e50; font-weight: 600;"
        )
        layout.addWidget(title_label)

        # Description
        if desc:
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("font-size: 11px; color: #95a5a6;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        self.setLayout(layout)