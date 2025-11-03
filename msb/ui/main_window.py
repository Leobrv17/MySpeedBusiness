from __future__ import annotations
import logging
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStatusBar, QToolBar, QMessageBox, QTabWidget, QLabel, QFileDialog
)

from msb.core.constants import APP_NAME
from msb.services.import_service import ImportService
from msb.services.export_service import ExportService
from msb.services.persistence import Persistence
from msb.ui.dialogs.new_event_dialog import NewEventDialog
from msb.ui.pages.participants_page import ParticipantsPage
from msb.ui.pages.settings_page import SettingsPage
from msb.ui.pages.plan_page import PlanPage

log = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, import_service: ImportService, export_service: ExportService) -> None:
        super().__init__()
        self.import_service = import_service
        self.export_service = export_service
        self.persistence = Persistence()

        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)

        # Tabs / pages
        central = QWidget(self)
        v = QVBoxLayout(central)
        self.tabs = QTabWidget(self)
        v.addWidget(self.tabs)
        self.setCentralWidget(central)

        self.page_participants = ParticipantsPage(self.persistence, on_ratio_changed=self._update_lead_ratio)
        self.page_settings = SettingsPage(self.persistence, on_changed=self._on_params_changed)
        self.page_plan = PlanPage(self.persistence)

        self.tabs.addTab(self.page_participants, "Participants")
        self.tabs.addTab(self.page_settings, "Settings")
        self.tabs.addTab(self.page_plan, "Plan de table")

        # StatusBar
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.lbl_event = QLabel("Aucune réunion", self)
        self.lbl_ratio = QLabel("Chefs de table: 0/0", self)
        self.status.addPermanentWidget(self.lbl_event)
        self.status.addPermanentWidget(self.lbl_ratio)

        # Menus & Toolbar
        self._create_actions()
        self._create_menus()
        self._create_toolbar()

    # --- Actions/menus/toolbar
    def _create_actions(self) -> None:
        self.act_new = QAction("Nouvelle réunion…", self); self.act_new.setShortcut(QKeySequence.New)
        self.act_open = QAction("Ouvrir…", self); self.act_open.setShortcut(QKeySequence.Open)
        self.act_close = QAction("Fermer la réunion", self)
        self.act_quit = QAction("Quitter", self); self.act_quit.setShortcut(QKeySequence.Quit)

        self.act_import_excel = QAction("Importer depuis Excel…", self)
        self.act_import_ui = QAction("Ajouter en masse (UI)…", self)
        self.act_export_excel = QAction("Exporter Excel…", self)
        self.act_export_badges = QAction("Exporter badges (PDF)…", self)

        self.act_new.triggered.connect(self.on_new_event)
        self.act_open.triggered.connect(self.on_open_event)
        self.act_close.triggered.connect(self.on_close_event)
        self.act_quit.triggered.connect(self.close)

        self.act_import_excel.triggered.connect(self._todo)
        self.act_import_ui.triggered.connect(self._todo)
        self.act_export_excel.triggered.connect(self._todo)
        self.act_export_badges.triggered.connect(self._todo)

    def _create_menus(self) -> None:
        bar = self.menuBar()
        m_file = bar.addMenu("&Fichier")
        m_file.addAction(self.act_new)
        m_file.addAction(self.act_open)
        m_file.addAction(self.act_close)
        m_file.addSeparator()
        m_file.addAction(self.act_quit)

        m_import = bar.addMenu("&Importer")
        m_import.addAction(self.act_import_excel)
        m_import.addAction(self.act_import_ui)

        m_export = bar.addMenu("&Exporter")
        m_export.addAction(self.act_export_excel)
        m_export.addAction(self.act_export_badges)

    def _create_toolbar(self) -> None:
        tb = QToolBar("Actions", self)
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.addToolBar(Qt.TopToolBarArea, tb)
        tb.addAction(self.act_new)
        tb.addAction(self.act_open)
        tb.addAction(self.act_close)
        tb.addSeparator()
        tb.addAction(self.act_import_excel)
        tb.addAction(self.act_import_ui)
        tb.addSeparator()
        tb.addAction(self.act_export_excel)
        tb.addAction(self.act_export_badges)

    # --- Handlers
    def _todo(self):
        QMessageBox.information(self, "À implémenter", "Cette fonctionnalité sera ajoutée ultérieurement.")

    def on_new_event(self):
        dlg = NewEventDialog(self)
        if not dlg.exec(): return
        name, start, end = dlg.get_values()
        if not name:
            QMessageBox.warning(self, "Nom requis", "Merci de renseigner un nom d'événement."); return
        # choisir l’emplacement du fichier .db
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer la réunion", "", "SQLite DB (*.db)")
        if not path: return
        db_path = Path(path)
        self.persistence.new_event(db_path, name, start, end)
        self._after_open_or_create()

    def on_open_event(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir une réunion", "", "SQLite DB (*.db)")
        if not path: return
        self.persistence.open_event(Path(path))
        self._after_open_or_create()

    def on_close_event(self):
        self.persistence.close_event()
        self.lbl_event.setText("Aucune réunion")
        self.lbl_ratio.setText("Chefs de table: 0/0")
        # vider les pages
        self.page_participants.reload()
        self.page_settings.load_from_event()
        self.page_plan.clear_views()

    def _after_open_or_create(self):
        info = self.persistence.get_event_info()
        self.lbl_event.setText(f"Événement: {info['name']}")
        # charger les pages
        self.page_participants.reload()
        self.page_settings.load_from_event()
        self.page_plan.load_existing_plan()
        self._update_lead_ratio()

    def _on_params_changed(self):
        self._update_lead_ratio()

    def _update_lead_ratio(self):
        try:
            leads, total = self.persistence.count_leads()
            self.lbl_ratio.setText(f"Chefs de table: {leads}/{total}")
            if hasattr(self, "page_settings"):
                self.page_settings.load_from_event()
        except RuntimeError:
            self.lbl_ratio.setText("Chefs de table: 0/0")

