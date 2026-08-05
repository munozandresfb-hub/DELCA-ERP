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
    datas=[],
    hiddenimports=[
        # PySide6
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtSvg",
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
        "src.modules.automatizacion.services.automatizacion_service",
        "src.modules.clientes.services.cliente_service",
        "src.modules.clientes.viewmodels.cliente_viewmodel",
        "src.modules.clientes.repositories.cliente_repository",
        "src.modules.llantas.services.llanta_service",
        "src.modules.llantas.viewmodels.llanta_viewmodel",
        "src.modules.finanzas.services.factura_service",
        "src.modules.inventario.services.producto_service",
        "src.modules.reportes.services.reporte_service",
        "src.modules.usuarios.services.auth_service",
        "src.modules.usuarios.viewmodels.login_viewmodel",
        "src.modules.usuarios.use_cases.bootstrap_admin",
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
