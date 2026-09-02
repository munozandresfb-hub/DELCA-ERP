# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for DELCA ERP."""

import sys
import os

sys.setrecursionlimit(5000)

PROJECT_DIR = os.getcwd()

a = Analysis(
    ["main.py"],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=[
        # Datos maestros para poblar catálogos en instalación limpia
        ("data/datos_maestros.xlsx", "data"),
        # Assets: hoja de proceso (fondo de impresión) + icono
        ("assets/hoja_proceso_reencauche.png", "assets"),
        ("assets/hoja_proceso_reencauche_v.png", "assets"),
        ("assets/delca.ico", "assets"),
    ],
    hiddenimports=[
        # PySide6
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
        "PySide6.QtPrintSupport",
        # SQLAlchemy
        "sqlalchemy",
        "sqlalchemy.sql.default_comparator",
        # All modules (dynamic imports from main.py)
        "src.database.base",
        "src.database.engine",
        "src.modules.usuarios.models.rol_model",
        "src.modules.usuarios.models.usuario_model",
        "src.modules.clientes.models.cliente_model",
        "src.modules.llantas.models.llanta_model",
        "src.modules.llantas.models.estado_llanta_model",
        "src.modules.llantas.models.ubicacion_llanta_model",
        "src.modules.finanzas.models.factura_model",
        "src.modules.finanzas.models.pago_model",
        "src.modules.inventario.models.producto_model",
        "src.modules.inventario.models.movimiento_inventario_model",
        "src.modules.auditoria.models.auditoria_model",
        "src.modules.automatizacion.models.regla_model",
        # Services
        "src.core.services.dashboard_service",
        "src.core.services.backup_service",
        "src.modules.automatizacion.services.automatizacion_service",
        "src.modules.clientes.services.cliente_service",
        "src.modules.clientes.viewmodels.cliente_viewmodel",
        "src.modules.clientes.repositories.cliente_repository",
        "src.modules.llantas.services.llanta_service",
        "src.modules.llantas.services.tiquete_printer",
        "src.modules.llantas.viewmodels.llanta_viewmodel",
        "src.modules.finanzas.services.factura_service",
        "src.modules.inventario.services.producto_service",
        "src.modules.reportes.services.reporte_service",
        "src.modules.usuarios.services.auth_service",
        "src.modules.usuarios.viewmodels.login_viewmodel",
        "src.modules.usuarios.use_cases.bootstrap_admin",
        # Migraciones (run_migration_once las importa dinámicamente)
        "scripts.migration_utils",
        "scripts.cargar_datos_maestros",
        "scripts.migrate_v1_0_0_schema",
        "scripts.migrate_v1_1_0_garantia",
        "scripts.migrate_v1_2_0_llantas",
        "scripts.migrate_v1_3_0_facturacion",
        "scripts.migrate_v1_4_0_inventario",
        "scripts.migrate_v1_4_0_costo_produccion",
        "scripts.migrate_v1_5_0_eliminar_produccion_detenida",
        "scripts.migrate_v1_6_0_fusionar_consulta_en_operador",
        "scripts.migrate_v1_7_0_ubicacion_actual",
        "scripts.migrate_v1_8_0_asesor",
        "scripts.migrate_v2_5_0_reproceso",
        "scripts.migrate_v2_6_0_dimension_ancho_float",
    ],
    hookspath=[],
    hooksconfig={},
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "PIL",
        "numpy",
        "pandas",
        "notebook",
        "jupyter",
        "IPython",
        "setuptools._distutils",
    ],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DELCA ERP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
