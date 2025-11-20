from __future__ import annotations
import logging
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from msb.core.constants import APP_NAME
from msb.services.import_service import ImportService
from msb.services.export_service import ExportService
from msb.services.persistence import Persistence
from msb.ui.dialogs.new_event_dialog import NewEventDialog
from msb.ui.dialogs.bulk_add_dialog import BulkAddDialog
from msb.ui.pages.participants_page import ParticipantsPage
from msb.ui.pages.settings_page import SettingsPage
from msb.ui.pages.plan_page import PlanPage

log = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(
        self,
        import_service: ImportService,
        export_service: ExportService,
        persistence: Persistence | None = None,
    ) -> None:
        super().__init__()
        self.import_service = import_service
        self.export_service = export_service
        self.persistence = persistence or Persistence()
        if hasattr(self.import_service, "persistence"):
            self.import_service.persistence = self.persistence
        if hasattr(self.export_service, "persistence"):
            self.export_service.persistence = self.persistence

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
        self.act_export_excel = QAction("Exporter plan (Excel)…", self)
        self.act_export_template = QAction("Exporter exemple d'import (Excel)…", self)
        self.act_export_badges = QAction("Exporter badges (PDF)…", self)

        self.act_new.triggered.connect(self.on_new_event)
        self.act_open.triggered.connect(self.on_open_event)
        self.act_close.triggered.connect(self.on_close_event)
        self.act_quit.triggered.connect(self.close)

        self.act_import_excel.triggered.connect(self.on_import_excel)
        self.act_import_ui.triggered.connect(self.on_import_ui)
        self.act_export_excel.triggered.connect(self.on_export_excel)
        self.act_export_template.triggered.connect(self.on_export_template)
        self.act_export_badges.triggered.connect(self.on_export_badges)

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
        m_export.addAction(self.act_export_template)
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
        tb.addAction(self.act_export_template)
        tb.addAction(self.act_export_badges)

    # --- Handlers
    def on_import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importer depuis Excel", "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            added = self.import_service.import_from_excel(path)
        except Exception as exc:
            log.exception("Import Excel échoué")
            QMessageBox.critical(self, "Erreur d'import", str(exc))
            return

        self.page_participants.reload()
        self._update_lead_ratio()
        QMessageBox.information(self, "Import terminé", f"{added} participant(s) importé(s).")

    def on_import_ui(self):
        dlg = BulkAddDialog(self)
        if not dlg.exec():
            return
        rows = dlg.get_rows()
        if not rows:
            QMessageBox.information(self, "Aucune ligne", "Aucun participant détecté dans le texte fourni.")
            return
        try:
            added = self.import_service.import_from_ui(rows)
        except Exception as exc:
            log.exception("Ajout en masse échoué")
            QMessageBox.critical(self, "Erreur", str(exc))
            return

        self.page_participants.reload()
        self._update_lead_ratio()
        QMessageBox.information(self, "Import terminé", f"{added} participant(s) ajouté(s).")

    def on_export_excel(self):
        try:
            info = self.persistence.get_event_info()
            plan = self.persistence.load_plan()
        except RuntimeError:
            QMessageBox.warning(self, "Aucune réunion", "Ouvrez ou créez une réunion avant d'exporter.")
            return

        if not plan:
            QMessageBox.warning(self, "Aucun plan", "Générez ou chargez un plan de table avant d'exporter le plan.")
            return

        suggested = f"{(info.get('name') or 'plan').strip() or 'plan'}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Exporter le plan Excel", suggested, "Excel (*.xlsx)")
        if not path:
            return

        try:
            output = self.export_service.export_plan_excel(Path(path))
        except Exception as exc:
            log.exception("Export Excel échoué")
            QMessageBox.critical(self, "Erreur d'export", str(exc))
            return

        QMessageBox.information(self, "Export terminé", f"Fichier généré : {output}")

    def on_export_template(self):
        try:
            info = self.persistence.get_event_info()
        except RuntimeError:
            QMessageBox.warning(self, "Aucune réunion", "Ouvrez ou créez une réunion avant d'exporter.")
            return

        suggested = f"{(info.get('name') or 'participants').strip() or 'participants'}_modele.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Exporter un exemple pour import", suggested, "Excel (*.xlsx)")
        if not path:
            return

        try:
            output = self.export_service.export_import_template(Path(path))
        except Exception as exc:
            log.exception("Export du modèle Excel échoué")
            QMessageBox.critical(self, "Erreur d'export", str(exc))
            return

        QMessageBox.information(self, "Export terminé", f"Modèle généré : {output}")

    def on_export_badges(self):
        try:
            info = self.persistence.get_event_info()
        except RuntimeError:
            QMessageBox.warning(self, "Aucune réunion", "Ouvrez ou créez une réunion avant d'exporter.")
            return

        event_name = (info.get("name") or "badges").strip()
        suggested = f"{event_name or 'badges'}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Exporter les badges", suggested, "PDF (*.pdf)")
        if not path:
            return

        try:
            output = self.export_service.export_badges_pdf(Path(path))
        except Exception as exc:
            log.exception("Export des badges échoué")
            QMessageBox.critical(self, "Erreur d'export", str(exc))
            return

        QMessageBox.information(self, "Export terminé", f"Badges exportés vers {output}")

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
        # Rafraîchir libellé d'événement (nom) + ratio chefs
        try:
            info = self.persistence.get_event_info()
            self.lbl_event.setText(f"Événement: {info['name']}")
        except RuntimeError:
            pass
        self._update_lead_ratio()

    def _update_lead_ratio(self):
        try:
            leads, total = self.persistence.count_leads()
            self.lbl_ratio.setText(f"Chefs de table: {leads}/{total}")
            if hasattr(self, "page_settings"):
                self.page_settings.load_from_event()
        except RuntimeError:
            self.lbl_ratio.setText("Chefs de table: 0/0")

