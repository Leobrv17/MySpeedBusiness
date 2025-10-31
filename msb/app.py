from __future__ import annotations
import logging, sys
from PySide6.QtWidgets import QApplication
from msb.core.config import load_config
from msb.core.logging import setup_logging
from msb.core.constants import APP_NAME, APP_VERSION
from msb.services.import_service import ImportService
from msb.services.export_service import ExportService
from msb.ui.main_window import MainWindow

def main() -> int:
    app = QApplication(sys.argv)
    cfg = load_config()
    setup_logging(cfg.data_dir / "logs")
    logging.getLogger(__name__).info("%s %s démarré", APP_NAME, APP_VERSION)

    import_svc = ImportService()   # placeholders
    export_svc = ExportService()

    win = MainWindow(import_svc, export_svc)

    if cfg.theme_path.exists():
        with open(cfg.theme_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
