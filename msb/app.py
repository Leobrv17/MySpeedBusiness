from __future__ import annotations
import logging, sys
from pathlib import Path
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from msb.core.config import load_config
from msb.core.logging import setup_logging
from msb.core.constants import APP_NAME, APP_VERSION
from msb.services.import_service import ImportService
from msb.services.export_service import ExportService
from msb.services.persistence import Persistence
from msb.ui.main_window import MainWindow
from msb.ui.theme import ThemeManager   # ✅

def main() -> int:
    app = QApplication(sys.argv)

    app_icon = Path(__file__).resolve().parent.parent / "img" / "msb_logo.png"
    app.setWindowIcon(QIcon(str(app_icon)))

    cfg = load_config()
    setup_logging(cfg.data_dir / "logs")
    logging.getLogger(__name__).info("%s %s démarré", APP_NAME, APP_VERSION)

    persistence = Persistence()

    import_svc = ImportService(persistence)
    export_svc = ExportService(persistence=persistence)
    win = MainWindow(import_service=import_svc, export_service=export_svc, persistence=persistence)

    dark_qss = Path("msb/ui/style_dark.qss")
    theme_mgr = ThemeManager(app, light_qss=cfg.theme_path, dark_qss=dark_qss)
    app.installEventFilter(theme_mgr)
    theme_mgr.auto_apply()
    win.theme_mgr = theme_mgr

    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
