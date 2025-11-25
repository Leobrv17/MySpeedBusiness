# -*- mode: python ; coding: utf-8 -*-
"""Configuration PyInstaller pour générer les exécutables MySpeedBusiness.

Cette spec inclut les ressources Qt nécessaires (feuilles de style et icônes)
avec un agencement identique à celui du dépôt pour simplifier les accès aux
fichiers via ``get_resources_root``.
"""

import pathlib
import sys

spec_path = pathlib.Path(globals().get("__file__", sys.argv[0])).resolve()
project_root = spec_path.parent.parent

# Emplacements de sortie explicites
build_root = project_root / "build" / "pyinstaller"
dist_root = project_root / "dist"

block_cipher = None

RESOURCE_DATAS = [
    (project_root / "img" / "msb_logo.png", "img"),
    (project_root / "img" / "bni_logo.png", "img"),
    (project_root / "msb" / "ui" / "style.qss", "msb/ui"),
    (project_root / "msb" / "ui" / "style_dark.qss", "msb/ui"),
]

a = Analysis(
    [str(project_root / "msb" / "app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(src), dest) for src, dest in RESOURCE_DATAS],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MySpeedBusiness',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MySpeedBusiness',
    workpath=str(build_root / "collect"),
    distpath=str(dist_root),
)
