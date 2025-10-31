from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

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
