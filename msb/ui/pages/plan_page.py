from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem, QMessageBox
from PySide6.QtCore import Qt
from msb.services.persistence import Persistence
from msb.services.planner import Planner

class PlanPage(QWidget):
    def __init__(self, persistence: Persistence):
        super().__init__()
        self.p = persistence
        self.planner = Planner()

        v = QVBoxLayout(self)
        self.btn_generate = QPushButton("Générer/Mettre à jour le plan", self)
        self.btn_generate.clicked.connect(self.generate_plan)
        v.addWidget(self.btn_generate)

        self.tabs = QTabWidget(self)
        self.tab_by_table = QTableWidget(self)
        self.tab_by_participant = QTableWidget(self)
        self.tabs.addTab(self.tab_by_table, "Vue par table")
        self.tabs.addTab(self.tab_by_participant, "Vue par participant")
        v.addWidget(self.tabs)

    def clear_views(self):
        self.tab_by_table.clear(); self.tab_by_participant.clear()

    def load_existing_plan(self):
        try:
            plan = self.p.load_plan()
        except RuntimeError:
            plan = []
        self.render_plan(plan)

    def generate_plan(self):
        try:
            info = self.p.get_event_info()
            parts = self.p.list_participants()
        except RuntimeError:
            QMessageBox.warning(self, "Aucun événement", "Créez/ouvrez une réunion d'abord."); return

        if (info["session_count"] or 0) <= 0 or (info["num_tables"] or 0) <= 0 or not parts:
            QMessageBox.warning(self, "Paramètres incomplets", "Vérifiez sessions, tables et participants."); return

        # on crée un objet Event-like pour le Planner
        class _E:
            pass
        e = _E()
        e.session_count = info["session_count"]; e.num_tables = info["num_tables"]
        e.table_capacity_min = info["cap_min"]; e.table_capacity_max = info["cap_max"]
        e.participants = [type("P", (), {"id": p.id, "first_name": p.first_name, "last_name": p.last_name, "job": p.job, "display_name": lambda self=f"{p.first_name} {p.last_name}": self}) for p in parts]

        sp = self.planner.build_plan(e)
        # Sauvegarde
        self.p.save_plan(sp.plan)
        # Rendu
        self.render_plan(sp.plan)

    def render_plan(self, plan):
        if not plan:
            self.clear_views(); return
        # Vue par table
        S = len(plan); T = len(plan[0]) if S>0 else 0
        self.tab_by_table.setRowCount(S); self.tab_by_table.setColumnCount(T)
        # on a besoin des noms depuis la DB
        try:
            parts = {p.id: p for p in self.p.list_participants()}
        except RuntimeError:
            parts = {}
        for s in range(S):
            for t in range(T):
                pids = plan[s][t]
                names = []
                for pid in pids:
                    p = parts.get(pid)
                    if p:
                        names.append(f"{p.first_name} {p.last_name} ({p.job})")
                item = QTableWidgetItem("\n".join(names))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.tab_by_table.setItem(s, t, item)
        self.tab_by_table.setHorizontalHeaderLabels([f"Table {i+1}" for i in range(T)])
        self.tab_by_table.setVerticalHeaderLabels([f"Session {i+1}" for i in range(S)])
        self.tab_by_table.resizeColumnsToContents(); self.tab_by_table.resizeRowsToContents()

        # Vue par participant
        try:
            ordered = list(self.p.list_participants())
        except RuntimeError:
            ordered = []
        self.tab_by_participant.setRowCount(len(ordered)); self.tab_by_participant.setColumnCount(S)
        for r, p in enumerate(ordered):
            for s in range(S):
                table_idx = "-"
                for t in range(T):
                    if p.id in plan[s][t]:
                        table_idx = t + 1; break
                item = QTableWidgetItem(str(table_idx))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.tab_by_participant.setItem(r, s, item)
        self.tab_by_participant.setVerticalHeaderLabels([f"{p.first_name} {p.last_name}" for p in ordered])
        self.tab_by_participant.setHorizontalHeaderLabels([f"S{i+1}" for i in range(S)])
        self.tab_by_participant.resizeColumnsToContents(); self.tab_by_participant.resizeRowsToContents()
