from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QObject, QEvent, QTimer
from PySide6.QtGui import QPalette, Qt
from PySide6.QtWidgets import QApplication


class ThemeManager(QObject):
    """
    Détecte clair/sombre et applique le QSS correspondant.
    Protégé contre les boucles via un verrou de ré-entrée et
    n'applique que si le mode a réellement changé.
    """
    def __init__(self, app: QApplication, light_qss: Path, dark_qss: Path) -> None:
        super().__init__()
        self.app = app
        self.light_qss = Path(light_qss)
        self.dark_qss = Path(dark_qss)
        self.current_mode: str | None = None  # 'light' | 'dark'
        self._applying: bool = False          # verrou anti-réentrance

    def is_system_dark(self) -> bool:
        # Qt 6.5+ : détection native
        hints = getattr(self.app, "styleHints", None)
        if hints:
            try:
                if hints().colorScheme() == Qt.ColorScheme.Dark:
                    return True
                if hints().colorScheme() == Qt.ColorScheme.Light:
                    return False
            except Exception:
                pass
        # Fallback : luminance de la palette
        pal = self.app.palette()
        bg = pal.color(QPalette.Window)
        luminance = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
        return luminance < 128

    def apply_mode(self, mode: str) -> None:
        if mode == self.current_mode:
            return
        qss_path = self.dark_qss if mode == "dark" else self.light_qss
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                self.app.setStyleSheet(f.read())
        self.current_mode = mode

    def auto_apply(self) -> None:
        mode = "dark" if self.is_system_dark() else "light"
        self.apply_mode(mode)

    def eventFilter(self, obj, event) -> bool:
        et = event.type()
        if et in (
            QEvent.ApplicationPaletteChange,
            QEvent.PaletteChange,
            QEvent.StyleChange,
            getattr(QEvent, "ThemeChange", 1000),  # 1000 = valeur bidon si pas dispo
        ):
            if not self._applying:
                # Détermine le mode souhaité
                desired = "dark" if self.is_system_dark() else "light"
                if desired != self.current_mode:
                    self._applying = True
                    # Appliquer au prochain tour d'event pour éviter la boucle immédiate
                    QTimer.singleShot(0, self._apply_deferred(desired))
        return super().eventFilter(obj, event)

    def _apply_deferred(self, mode: str):
        def _do():
            try:
                self.apply_mode(mode)
            finally:
                self._applying = False
        return _do
