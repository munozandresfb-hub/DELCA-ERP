import sys

from PySide6.QtWidgets import QApplication

from src.database.base import Base
from src.database.engine import engine

# ─── Registrar todos los modelos (orden seguro de dependencias) ───
import src.database.registry  # noqa: F401

from src.modules.usuarios.use_cases.bootstrap_admin import bootstrap_admin
from src.modules.usuarios.views.login_window import LoginWindow

Base.metadata.create_all(bind=engine)

# ─── Migraciones (orden cronológico, cada una corre una sola vez) ────
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
]

for version, path in _MIGRACIONES:
    try:
        run_migration_once(version, path)
    except Exception as e:
        print(f"[main] Error en migración {version}: {e}")

# ─── Bootstrap admin (después de migraciones para evitar inconsistencias) ──
bootstrap_admin()

# ─── Inicializar reglas de automatización ───
from src.modules.automatizacion.services.automatizacion_service import AutomatizacionService

AutomatizacionService.inicializar_reglas()

app = QApplication(sys.argv)

window = LoginWindow()
window.show()

sys.exit(app.exec())