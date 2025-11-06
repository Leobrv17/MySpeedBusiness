from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from .constants import APP_NAME

@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    theme_path: Path

def load_config() -> AppConfig:
    base = Path.cwd()
    data_dir = base / "data"
    theme_path = base / "msb" / "ui" / "style.qss"
    data_dir.mkdir(parents=True, exist_ok=True)
    return AppConfig(data_dir=data_dir, theme_path=theme_path)

def is_system_dark(app: QApplication) -> bool:
    """Détecte si le thème système est sombre."""
    palette = app.palette()
    bg_color = palette.color(QPalette.Window)
    # Valeur simple : si la luminosité moyenne est faible, on est en sombre
    brightness = (bg_color.red() * 0.299 + bg_color.green() * 0.587 + bg_color.blue() * 0.114)
    return brightness < 128
