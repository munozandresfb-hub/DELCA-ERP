"""Punto de entrada de DELCA ERP.

Orden del arranque:
  1. QApplication y SPLASH se crean INMEDIATAMENTE (la ventana aparece al
     instante, nada de pantalla negra).
  2. Los imports pesados (modelos, migraciones, vistas) se cargan DESPUÉS
     del splash para que la UI responda de inmediato.
  3. Las migraciones / bootstrap / reglas corren con el splash visible y
     ``processEvents`` para que el splash se repinte.
  4. Al terminar se cierra el splash y se muestra el LoginWindow.

Cualquier error de arranque queda registrado en el log y se muestra en un
QMessageBox (importante porque la app se lanza con ``pythonw`` sin consola).
"""

import logging
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen

logger = logging.getLogger("delca.startup")

# Icono de la aplicación (barra de título, taskbar, alt-tab)
ICONO_APP = Path(__file__).resolve().parent / "assets" / "delca.ico"


# ─── Splash (sin assets externos: se dibuja programáticamente) ──────────
def _crear_splash() -> QSplashScreen:
    """Splash con branding DELCA generado en memoria (sin archivos)."""
    ancho, alto = 520, 300
    pixmap = QPixmap(ancho, alto)
    pixmap.fill(QColor("#1a252f"))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Fondo con gradiente
    grad = QLinearGradient(0, 0, 0, alto)
    grad.setColorAt(0.0, QColor("#1a252f"))
    grad.setColorAt(1.0, QColor("#2c3e50"))
    painter.fillRect(0, 0, ancho, alto, grad)

    # Banda superior verde institucional
    painter.fillRect(0, 0, ancho, 6, QColor("#27ae60"))

    # Título
    painter.setPen(QColor("#ffffff"))
    title_font = QFont("Segoe UI", 30, QFont.Bold)
    painter.setFont(title_font)
    painter.drawText(
        0, 70, ancho, 60, Qt.AlignCenter, "DELCA ERP"
    )

    # Subtítulo
    painter.setPen(QColor("#9fb3c8"))
    sub_font = QFont("Segoe UI", 12)
    painter.setFont(sub_font)
    painter.drawText(
        0, 130, ancho, 40, Qt.AlignCenter,
        "Sistema de Gestión · Reencauchadora",
    )

    # Indicador de carga (texto que se actualiza con showMessage)
    painter.setPen(QColor("#7f8c8d"))
    load_font = QFont("Segoe UI", 9)
    painter.setFont(load_font)
    painter.drawText(
        0, 190, ancho, 30, Qt.AlignCenter, "Cargando..."
    )

    painter.end()
    return QSplashScreen(pixmap)


def main() -> int:
    app = QApplication(sys.argv)

    # Icono de la app (taskbar, barra de título, alt-tab)
    if ICONO_APP.exists():
        app.setWindowIcon(QIcon(str(ICONO_APP)))

    splash = _crear_splash()
    splash.show()
    app.processEvents()

    try:
        # ─── Imports pesados (después del splash) ────────────────────
        from src.database.base import Base
        from src.database.engine import engine

        # Registrar todos los modelos (orden seguro de dependencias)
        import src.database.registry  # noqa: F401

        splash.showMessage("Verificando base de datos...", Qt.AlignBottom | Qt.AlignHCenter, QColor("#27ae60"))
        app.processEvents()
        Base.metadata.create_all(bind=engine)

        # ─── Migraciones (orden cronológico, cada una corre una sola vez) ──
        from scripts.migration_utils import run_migration_once

        _MIGRACIONES: list[tuple[str, str]] = [
            ("v1.0.0",               "scripts.migrate_v1_0_0_schema"),
            ("v1.1.0",               "scripts.migrate_v1_1_0_garantia"),
            ("v1.2.0",               "scripts.migrate_v1_2_0_llantas"),
            ("v1.3.0",               "scripts.migrate_v1_3_0_facturacion"),
            ("v1.4.0_inventario",    "scripts.migrate_v1_4_0_inventario"),
            ("v1.4.0_costo",         "scripts.migrate_v1_4_0_costo_produccion"),
            ("v1.5.0",               "scripts.migrate_v1_5_0_eliminar_produccion_detenida"),
            ("v1.6.0",               "scripts.migrate_v1_6_0_fusionar_consulta_en_operador"),
            ("v1.7.0",               "scripts.migrate_v1_7_0_ubicacion_actual"),
            ("v1.8.0",               "scripts.migrate_v1_8_0_asesor"),
            ("v2.5.0",               "scripts.migrate_v2_5_0_reproceso"),
            ("v2.6.0",               "scripts.migrate_v2_6_0_dimension_ancho_float"),
        ]

        for version, path in _MIGRACIONES:
            try:
                run_migration_once(version, path)
            except Exception as e:
                print(f"[main] Error en migración {version}: {e}")

        # ─── Bootstrap admin (después de migraciones) ────────────────
        from src.modules.usuarios.use_cases.bootstrap_admin import bootstrap_admin

        splash.showMessage("Preparando sesión...", Qt.AlignBottom | Qt.AlignHCenter, QColor("#27ae60"))
        app.processEvents()
        bootstrap_admin()

        # ─── Datos maestros (instalación limpia: pobla catálogos) ────
        try:
            from scripts.cargar_datos_maestros import inicializar_datos_maestros

            inicializar_datos_maestros(only_if_empty=True)
        except Exception as e:
            print(f"[main] Error cargando datos maestros: {e}")

        # ─── Inicializar reglas de automatización ────────────────────
        from src.modules.automatizacion.services.automatizacion_service import (
            AutomatizacionService,
        )

        AutomatizacionService.inicializar_reglas()

        # ─── Login ───────────────────────────────────────────────────
        from src.modules.usuarios.views.login_window import LoginWindow

        window = LoginWindow()
        splash.finish(window)
        window.show()

    except Exception:
        logger.error("Error de arranque:\n%s", traceback.format_exc())
        splash.close()
        QMessageBox.critical(
            None,
            "Error de arranque",
            "DELCA ERP no pudo iniciarse correctamente.\n\n"
            "Detalles:\n" + traceback.format_exc(limit=3),
        )
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())