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
            rows = list(self.p.list_participants())
        except RuntimeError:
            QMessageBox.warning(self, "Aucun événement", "Créez/ouvrez une réunion d'abord.");
            return

        leads = [r for r in rows if r.is_table_lead]
        rot = [r for r in rows if not r.is_table_lead]
        T = len(leads)
        if T == 0:
            QMessageBox.warning(self, "Aucun chef de table", "Sélectionnez au moins un chef de table.");
            return

        # Capacité cible bornée 5..10 (chef inclus)
        cap_min = max(5, info["cap_min"] or 5)
        cap_max = min(10, max(cap_min, info["cap_max"] or 10))
        R = len(rot)
        target_k = int(round(R / max(1, T) + 1))  # +1 car chef
        k = max(cap_min, min(cap_max, target_k))
        rot_per_table = max(1, k - 1)

        # Sessions S (S ≤ T, et borne Social Golfer approximative)
        S = max(1, min(info["session_count"] or 1, T))
        if k >= 3 and R > 1:
            r_sg = (R - 1) // (k - 2)
            S = min(S, max(1, r_sg))

        # Nouveau planner: renvoie seulement les rotatifs par table
        planner_plan = self.planner.build_plan(
            leads=[p.id for p in leads],
            rotators=[p.id for p in rot],
            sessions=S,
            rot_per_table=rot_per_table,
            seed=None,
        )

        # Construire le plan "complet" en ajoutant le chef fixe en premier dans chaque table
        full_plan: list[list[list[int]]] = []
        for s_idx in range(S):
            session_tables: list[list[int]] = []
            for t_idx in range(T):
                row_ids = [leads[t_idx].id]  # chef en tête
                if s_idx < len(planner_plan):
                    row_ids.extend(planner_plan[s_idx][t_idx])
                session_tables.append(row_ids)
            full_plan.append(session_tables)

        # Sauvegarde DB et rendu
        self.p.save_plan(full_plan)
        self.render_plan(full_plan)

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
