# -*- mode: python ; coding: utf-8 -*-
"""Configuration PyInstaller pour générer les exécutables MySpeedBusiness.

Cette spec inclut les ressources Qt nécessaires (feuilles de style et icônes)
avec un agencement identique à celui du dépôt pour simplifier les accès aux
fichiers via ``get_resources_root``.
"""

import pathlib
import sys

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - erreur claire en phase build
    raise SystemExit(
        "Pillow est requis pour générer les icônes .ico/.icns lors du packaging PyInstaller."
    ) from exc

spec_path = pathlib.Path(globals().get("__file__", sys.argv[0])).resolve()
project_root = spec_path.parent.parent
icon_root = project_root / "build" / "pyinstaller" / "icons"
is_macos = sys.platform == "darwin"


def build_icon(target: pathlib.Path, fmt: str) -> pathlib.Path:
    """Génère un fichier icône à partir du PNG source.

    On évite de versionner des binaires .ico/.icns : ils sont produits à la
    volée dans ``build/pyinstaller/icons`` pour Windows et macOS.
    """

    source_png = project_root / "img" / "msb_logo.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image = Image.open(source_png)

    save_kwargs = {}
    if fmt == "ICO":
        # Nécessaire pour que l'icône apparaisse correctement dans la barre des tâches
        save_kwargs["sizes"] = [(256, 256)]

    image.save(target, format=fmt, **save_kwargs)
    return target


app_icon = build_icon(icon_root / "msb_logo.ico", "ICO")
app_icon_macos = build_icon(icon_root / "msb_logo.icns", "ICNS")

# Emplacements de sortie explicites
build_root = project_root / "build" / "pyinstaller"
dist_root = project_root / "dist"

block_cipher = None

RESOURCE_DATAS = [
    (project_root / "img" / "msb_logo.png", "img"),
    (project_root / "img" / "msb_logo.ico", "img"),
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
    icon=str(project_root / "img" / "msb_logo.ico") if not is_macos else None,
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
    icon=str(app_icon),
)

target = exe
if is_macos:
    # BUNDLE construit le .app mais COLLECT doit recevoir un EXE.
    mac_bundle = BUNDLE(
        exe,
        name="MySpeedBusiness.app",
        icon=str(app_icon_macos),
        bundle_identifier="com.myspeedbusiness.app",
    )
    target = mac_bundle

coll = COLLECT(
    target,
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
