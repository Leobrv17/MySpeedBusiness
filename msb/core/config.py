from __future__ import annotations
from dataclasses import dataclass
import sys
from pathlib import Path
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from .constants import APP_NAME

@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    theme_path: Path


def get_resources_root() -> Path:
    """Retourne le dossier racine où se trouvent les ressources embarquées.

    Lorsqu'on exécute l'application "gelée" par PyInstaller, les ressources
    sont extraites dans ``sys._MEIPASS``. En mode développement, on revient à
    la racine du dépôt pour garder le même agencement de fichiers.
    """

    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)

    return Path(__file__).resolve().parent.parent.parent


def get_run_root() -> Path:
    """Retourne le dossier contenant l'exécutable ou le projet en développement.

    Lorsqu'on exécute un binaire PyInstaller, le répertoire courant peut varier
    selon le mode de lancement (double-clic, terminal…). Pour garantir une
    zone d'écriture stable pour les logs et bases de données, on déduit la
    racine à partir du chemin de l'exécutable gelé.
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent.parent

def load_config() -> AppConfig:
    data_dir = get_run_root() / "data"
    theme_path = get_resources_root() / "msb" / "ui" / "style.qss"
    data_dir.mkdir(parents=True, exist_ok=True)
    return AppConfig(data_dir=data_dir, theme_path=theme_path)

def is_system_dark(app: QApplication) -> bool:
    """Détecte si le thème système est sombre."""
    palette = app.palette()
    bg_color = palette.color(QPalette.Window)
    # Valeur simple : si la luminosité moyenne est faible, on est en sombre
    brightness = (bg_color.red() * 0.299 + bg_color.green() * 0.587 + bg_color.blue() * 0.114)
    return brightness < 128
