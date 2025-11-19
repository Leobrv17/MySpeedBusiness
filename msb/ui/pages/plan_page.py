from __future__ import annotations
from msb.services.persistence import Persistence
from msb.services.planner import Planner
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QGroupBox, QHBoxLayout, QLabel, QDialog, QDialogButtonBox, QTextEdit
)
from PySide6.QtCore import Qt

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

        box = QGroupBox("Statut du plan", self)
        hb = QHBoxLayout(box)

        self.lbl_pairs_repeat = QLabel("Paires en doublon: 0", self)
        self.lbl_pairs_never = QLabel("Paires jamais rencontrées: 0", self)

        self.btn_show_repeat = QPushButton("Voir les doublons", self)
        self.btn_show_never = QPushButton("Voir les paires jamais rencontrées", self)

        self.btn_show_repeat.clicked.connect(self._show_repeat_pairs)
        self.btn_show_never.clicked.connect(self._show_never_pairs)

        hb.addWidget(self.lbl_pairs_repeat)
        hb.addSpacing(12)
        hb.addWidget(self.btn_show_repeat)
        hb.addSpacing(24)
        hb.addWidget(self.lbl_pairs_never)
        hb.addSpacing(12)
        hb.addWidget(self.btn_show_never)
        hb.addStretch(1)

        v.addWidget(box)

        # caches pour les listes détaillées
        self._last_pairs_repeat = []  # list[tuple[int,int]]
        self._last_pairs_never = []  # list[tuple[int,int]]

    def clear_views(self):
        self.tab_by_table.clear();
        self.tab_by_participant.clear()
        self._last_pairs_repeat = [];
        self._last_pairs_never = []
        self.lbl_pairs_repeat.setText("Paires en doublon: 0")
        self.lbl_pairs_never.setText("Paires jamais rencontrées: 0")

    def load_existing_plan(self):
        try:
            plan = self.p.load_plan()
        except RuntimeError:
            plan = []
        self.render_plan(plan)
        self._update_stats_panel(plan)

    def generate_plan(self):
        from PySide6.QtWidgets import QMessageBox

        # 1) Charger contexte
        try:
            info = self.p.get_event_info()
            rows = list(self.p.list_participants())
        except RuntimeError:
            QMessageBox.warning(self, "Aucun événement", "Créez/ouvrez une réunion d'abord.")
            return

        N = len(rows)
        if N == 0:
            QMessageBox.information(self, "Aucun participant", "Ajoutez des participants avant de générer.")
            return

        T = max(1, info.get("num_tables") or 1)

        # 2) Exiger 1 chef par table avant génération
        leads = [r for r in rows if r.is_table_lead]
        if len(leads) != T:
            QMessageBox.warning(
                self, "Chefs de table requis",
                f"Il faut sélectionner exactement {T} chef(s) de table (actuellement {len(leads)})."
            )
            return

        # 3) Faisabilité: tout le monde doit être assis, 5..10 par table
        # => condition nécessaire: 5*T <= N <= 10*T
        if N < 5 * T:
            QMessageBox.warning(
                self, "Capacité insuffisante",
                f"Avec {T} tables, il faut au moins {5 * T} participants (5 par table). "
                f"Participants actuels: {N}."
            )
            return
        if N > 10 * T:
            QMessageBox.warning(
                self, "Capacité dépassée",
                f"Avec {T} tables, on ne peut pas dépasser {10 * T} participants (10 par table). "
                f"Participants actuels: {N}. Augmentez le nombre de tables."
            )
            return

        # 4) Calcul des capacités exactes par table (5..10) avec somme == N
        # Stratégie: démarrer à 5 partout, puis distribuer le reste jusqu'à atteindre N (sans dépasser 10)
        caps = [5] * T
        remaining = N - 5 * T  # nombre de places à répartir pour atteindre N
        idx = 0
        while remaining > 0:
            if caps[idx] < 10:
                caps[idx] += 1
                remaining -= 1
            idx = (idx + 1) % T

        # 5) Préparer les IDs chefs fixes et les autres personnes
        #    (1 chef par table; on aligne les chefs aux tables 0..T-1 selon l'ordre actuel)
        lead_ids = [p.id for p in leads[:T]]
        fixed_lead_set = set(lead_ids)
        rotator_ids = [p.id for p in rows if p.id not in fixed_lead_set]

        # 6) Récupérer le nombre de sessions (priorité fixe à exclusivité)
        S = max(1, info.get("session_count") or 1)

        # 7) Générer le plan via le planner
        #    Planner attendu: build_plan(num_tables, sessions, table_capacities, fixed_leads, people)
        plan = self.planner.build_plan(
            num_tables=T,
            sessions=S,
            table_capacities=caps,
            fixed_leads=lead_ids,  # chefs fixes (optionnels, ici requis et fournis)
            people=rotator_ids
        )

        # 8) Sauvegarde en DB + rendu + stats
        self.p.save_plan(plan)
        self.render_plan(plan)
        if hasattr(self, "_update_stats_panel"):
            self._update_stats_panel(plan)

        QMessageBox.information(
            self, "Plan généré",
            f"Plan de {S} session(s) généré avec {T} table(s).\n"
            f"Capacités par table: {caps}\n"
            "Priorité: Exclusivité"
        )

    # ou raw_plan selon ce que tu passes à render_plan

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

    def _compute_plan_stats(self, plan):
        """
        Retourne:
          - repeated: list de paires (pid1,pid2) rencontrées >1 fois
          - never: list de paires (pid1,pid2) jamais rencontrées
        """
        if not plan:
            return [], []

        # Liste des participants impliqués dans le plan (depuis la DB pour être sûr)
        try:
            parts = list(self.p.list_participants())
        except RuntimeError:
            parts = []
        ids = [p.id for p in parts]
        id_index = {pid: i for i, pid in enumerate(ids)}
        n = len(ids)
        if n <= 1:
            return [], []

        # matrice comptant les rencontres par paire
        meets = [[0]*n for _ in range(n)]

        # pour chaque session/table, incrémente les rencontres entre tous les co-présents
        for tables in plan:
            for lst in tables:
                # lst = [chef?, rotatifs...] ; compte toutes les combinaisons 2 à 2
                for i in range(len(lst)):
                    for j in range(i+1, len(lst)):
                        a, b = lst[i], lst[j]
                        ia = id_index.get(a); ib = id_index.get(b)
                        if ia is None or ib is None:
                            continue
                        meets[ia][ib] += 1
                        meets[ib][ia] += 1

        repeated = []
        never = []
        for i in range(n):
            for j in range(i+1, n):
                if meets[i][j] == 0:
                    never.append((ids[i], ids[j]))
                elif meets[i][j] > 1:
                    repeated.append((ids[i], ids[j]))

        return repeated, never

    def _update_stats_panel(self, plan):
        rep, nev = self._compute_plan_stats(plan)
        self._last_pairs_repeat = rep
        self._last_pairs_never = nev
        self.lbl_pairs_repeat.setText(f"Paires en doublon: {len(rep)}")
        self.lbl_pairs_never.setText(f"Paires jamais rencontrées: {len(nev)}")

    def _show_repeat_pairs(self):
        self._show_pairs_dialog(self._last_pairs_repeat, "Paires en doublon (>1 fois)")

    def _show_never_pairs(self):
        self._show_pairs_dialog(self._last_pairs_never, "Paires jamais rencontrées")

    def _show_pairs_dialog(self, pairs, title):
        # map id -> participant
        try:
            parts = {p.id: p for p in self.p.list_participants()}
        except RuntimeError:
            parts = {}

        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        layout = QVBoxLayout(dlg)
        txt = QTextEdit(dlg); txt.setReadOnly(True)

        if not pairs:
            txt.setPlainText("Aucune paire.")
        else:
            lines = []
            for a, b in pairs:
                pa = parts.get(a); pb = parts.get(b)
                na = f"{pa.first_name} {pa.last_name}" if pa else str(a)
                nb = f"{pb.first_name} {pb.last_name}" if pb else str(b)
                lines.append(f"{na}  —  {nb}")
            txt.setPlainText("\n".join(lines))

        layout.addWidget(txt)
        btns = QDialogButtonBox(QDialogButtonBox.Close, parent=dlg)
        btns.rejected.connect(dlg.reject); btns.accepted.connect(dlg.accept)
        layout.addWidget(btns)
        dlg.resize(520, 420)
        dlg.exec()
