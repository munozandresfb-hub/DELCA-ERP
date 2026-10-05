# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para el VERIFICADOR de funcionalidad de DELCA ERP.

Genera un .exe autonomo (con consola) que corre en cualquier PC sin Python
ni dependencias, y valida la instalacion migrada (componentes + BD + reglas +
servicios).
"""

import os
import sys

sys.setrecursionlimit(5000)

PROJECT_DIR = os.getcwd()


def _modulos_proyecto() -> list[str]:
    modulos = []
    base = os.path.join(PROJECT_DIR, "src")
    for raiz, dirs, archivos in os.walk(base):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for archivo in archivos:
            if archivo.endswith(".py") and archivo != "__init__.py":
                ruta = os.path.join(raiz, archivo)
                rel = os.path.relpath(ruta, PROJECT_DIR)
                modulos.append(rel[:-3].replace(os.sep, "."))
    return modulos


hiddenimports_proyecto = _modulos_proyecto()

a = Analysis(
    ["scripts/verificar_migracion.py"],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=[],
    hiddenimports=[
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "sqlalchemy",
        "sqlalchemy.sql.default_comparator",
    ]
    + hiddenimports_proyecto,
    hookspath=[],
    hooksconfig={},
    excludes=[
        "tkinter", "matplotlib", "scipy", "PIL", "numpy", "pandas",
        "notebook", "jupyter", "IPython", "setuptools._distutils",
    ],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="verificar_migracion",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJECT_DIR, "assets", "delca.ico"),
)