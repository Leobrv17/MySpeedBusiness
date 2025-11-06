from __future__ import annotations
from dataclasses import dataclass
from math import ceil, floor
from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDateTimeEdit, QSpinBox, QCheckBox, QMessageBox, QButtonGroup
)
from msb.services.persistence import Persistence

@dataclass
class Settings:
    # Général
    name: str
    start: QDateTime
    end: QDateTime
    # Sessions
    num_tables: int
    cap_min: int
    cap_max: int
    session_count: int
    dur: int
    trans: int
    # Règles
    rule_priority: str  # "exclusivity" ou "coverage"
    # Pauses
    pause_count: int
    pause_minutes: int

class SettingsPage(QWidget):
    def __init__(self, persistence: Persistence, on_changed):
        super().__init__()
        self.p = persistence
        self.on_changed = on_changed

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        # ---------- Général ----------
        gb_general = QGroupBox("Général", self)
        flg = QFormLayout(gb_general)
        self.ev_name = QLineEdit(self)
        self.ev_start = QDateTimeEdit(self); self.ev_start.setCalendarPopup(True)
        self.ev_end = QDateTimeEdit(self); self.ev_end.setCalendarPopup(True)
        flg.addRow("Nom de l’événement", self.ev_name)
        flg.addRow("Début", self.ev_start)
        flg.addRow("Fin", self.ev_end)
        root.addWidget(gb_general)

        # ---------- Sessions ----------
        gb_sessions = QGroupBox("Sessions", self)
        fls = QFormLayout(gb_sessions)
        self.num_tables = QSpinBox(self); self.num_tables.setRange(0, 500)
        self.cap_min = QSpinBox(self); self.cap_min.setRange(1, 100); self.cap_min.setValue(5)
        self.cap_max = QSpinBox(self); self.cap_max.setRange(1, 100); self.cap_max.setValue(10)
        self.session_count = QSpinBox(self); self.session_count.setRange(0, 500)
        self.dur = QSpinBox(self); self.dur.setRange(1, 240); self.dur.setValue(10)
        self.trans = QSpinBox(self); self.trans.setRange(0, 60); self.trans.setValue(2)
        fls.addRow("Nombre de tables", self.num_tables)
        fls.addRow("Min par table", self.cap_min)
        fls.addRow("Max par table", self.cap_max)
        fls.addRow("Nombre de sessions", self.session_count)
        fls.addRow("Durée (minutes) / session", self.dur)
        fls.addRow("Transition (minutes)", self.trans)
        root.addWidget(gb_sessions)

        # ---------- Règles ----------
        gb_rules = QGroupBox("Règles de l’événement", self)
        vrr = QVBoxLayout(gb_rules)
        self.chk_exclusivity = QCheckBox("Priorité : exclusivité (chaque personne ne croise qu’une fois)", self)
        self.chk_coverage = QCheckBox("Priorité : couverture (tout le monde se croise au moins une fois)", self)
        # exclusivité des cases via QButtonGroup
        group = QButtonGroup(self); group.setExclusive(True)
        group.addButton(self.chk_exclusivity); group.addButton(self.chk_coverage)
        vrr.addWidget(self.chk_exclusivity)
        vrr.addWidget(self.chk_coverage)
        root.addWidget(gb_rules)

        # ---------- Pauses ----------
        gb_pause = QGroupBox("Pauses", self)
        flp = QFormLayout(gb_pause)
        self.pause_count = QSpinBox(self); self.pause_count.setRange(0, 20)
        self.pause_minutes = QSpinBox(self); self.pause_minutes.setRange(0, 120)
        flp.addRow("Nombre de pauses", self.pause_count)
        flp.addRow("Durée (minutes) / pause", self.pause_minutes)
        root.addWidget(gb_pause)

        # ---------- Bandeau d’info + Auto-tune ----------
        hb = QHBoxLayout()
        self.info = QLabel("", self)
        self.btn_auto = QPushButton("Trouver les meilleurs paramètres automatiquement", self)
        self.btn_auto.clicked.connect(self.auto_tune)
        hb.addWidget(self.info); hb.addStretch(1); hb.addWidget(self.btn_auto)
        root.addLayout(hb)

        # ---------- Signals (save on change) ----------
        self.ev_name.editingFinished.connect(self._apply_general)
        self.ev_start.dateTimeChanged.connect(self._apply_general)
        self.ev_end.dateTimeChanged.connect(self._apply_general)

        for w in (self.num_tables, self.cap_min, self.cap_max, self.session_count, self.dur, self.trans):
            w.valueChanged.connect(self._apply_sessions)

        self.chk_exclusivity.toggled.connect(self._apply_rules)
        self.chk_coverage.toggled.connect(self._apply_rules)

        for w in (self.pause_count, self.pause_minutes):
            w.valueChanged.connect(self._apply_pauses)

    # --------- Load / Apply ----------
    def load_from_event(self):
        try:
            info = self.p.get_event_info()
        except RuntimeError:
            # remise à zéro
            now = QDateTime.currentDateTime()
            self.ev_name.setText("")
            self.ev_start.setDateTime(now)
            self.ev_end.setDateTime(now.addSecs(2*3600))
            self.num_tables.setValue(0)
            self.cap_min.setValue(5)
            self.cap_max.setValue(10)
            self.session_count.setValue(0)
            self.dur.setValue(10)
            self.trans.setValue(2)
            self.chk_exclusivity.setChecked(True)
            self.chk_coverage.setChecked(False)
            self.pause_count.setValue(0)
            self.pause_minutes.setValue(0)
            self._update_info()
            return

        # Général
        self.ev_name.setText(info["name"] or "")
        self.ev_start.setDateTime(QDateTime(info["date_start"]))
        self.ev_end.setDateTime(QDateTime(info["date_end"]))
        # Sessions
        self.num_tables.setValue(info["num_tables"] or 0)
        self.cap_min.setValue(max(1, info["cap_min"] or 5))
        self.cap_max.setValue(max(self.cap_min.value(), info["cap_max"] or 10))
        self.session_count.setValue(info["session_count"] or 0)
        self.dur.setValue(info["dur"] or 10)
        self.trans.setValue(info["trans"] or 2)
        # Règles
        rp = (info["rule_priority"] or "exclusivity").lower()
        self.chk_exclusivity.setChecked(rp == "exclusivity")
        self.chk_coverage.setChecked(rp == "coverage")
        # Pauses
        self.pause_count.setValue(info["pause_count"] or 0)
        self.pause_minutes.setValue(info["pause_minutes"] or 0)

        # Auto-suggestion si 0 tables et participants existants
        if (info["num_tables"] or 0) == 0:
            try:
                n = len(self.p.list_participants())
                if n > 0:
                    self.num_tables.setValue(max(1, round(n / 8)))
                    self._apply_sessions()
            except RuntimeError:
                pass

        self._update_info()

    # Général
    def _apply_general(self):
        try:
            self.p.update_event_general(
                name=self.ev_name.text().strip(),
                date_start=self.ev_start.dateTime().toPython(),
                date_end=self.ev_end.dateTime().toPython(),
            )
        except RuntimeError:
            return
        self._update_info()
        if self.on_changed: self.on_changed()

    # Sessions
    def _apply_sessions(self):
        cap_min = min(self.cap_min.value(), self.cap_max.value())
        cap_max = max(self.cap_min.value(), self.cap_max.value())
        try:
            self.p.update_event_params(
                num_tables=self.num_tables.value(),
                cap_min=cap_min,
                cap_max=cap_max,
                session_count=self.session_count.value(),
                dur=self.dur.value(),
                trans=self.trans.value(),
            )
        except RuntimeError:
            return
        self._update_info()
        if self.on_changed: self.on_changed()

    # Règles
    def _apply_rules(self):
        rule = "exclusivity" if self.chk_exclusivity.isChecked() else "coverage"
        try:
            self.p.update_event_params(rule_priority=rule)
        except RuntimeError:
            return
        self._update_info()
        if self.on_changed: self.on_changed()

    # Pauses
    def _apply_pauses(self):
        try:
            self.p.update_event_params(
                pause_count=self.pause_count.value(),
                pause_minutes=self.pause_minutes.value(),
            )
        except RuntimeError:
            return
        self._update_info()
        if self.on_changed: self.on_changed()

    # Info bandeau
    def _update_info(self):
        try:
            info = self.p.get_event_info()
            n = len(self.p.list_participants())
        except RuntimeError:
            self.info.setText(""); return

        # budget théorique hors pauses
        total_minutes = max(0, int((info["date_end"] - info["date_start"]).total_seconds() // 60))
        pauses = (info["pause_count"] or 0) * (info["pause_minutes"] or 0)
        usable = max(0, total_minutes - pauses)
        slot = (info["dur"] or 0) + (info["trans"] or 0)
        sessions_fit = (usable // slot) if slot > 0 else 0

        rule_label = "Exclusivité" if (info["rule_priority"] or "exclusivity") == "exclusivity" else "Couverture"
        target_per_table = self._target_capacity(n, info["num_tables"] or 0, info["cap_min"] or 5, info["cap_max"] or 10)

        self.info.setText(
            f"Participants: {n} | Cible/table ≈ {target_per_table} | Budget utile ≈ {usable} min | "
            f"Sessions réalisables ≈ {sessions_fit} | Règle: {rule_label}"
        )

    @staticmethod
    def _target_capacity(n: int, T: int, cap_min: int, cap_max: int) -> int:
        if T <= 0: return cap_min
        return max(cap_min, min(cap_max, ceil(n / T)))

    # Auto-tune (réutilise ta logique, enverra aussi les pauses/règle si besoin)
    def auto_tune(self):
        try:
            info = self.p.get_event_info()
            participants = list(self.p.list_participants())
        except RuntimeError:
            QMessageBox.warning(self, "Aucun événement", "Créez/ouvrez une réunion d'abord.")
            return

        N = len(participants)
        if N == 0:
            QMessageBox.information(self, "Aucun participant", "Ajoutez des participants avant l’auto-tune.")
            return

        leads = [p for p in participants if p.is_table_lead]
        L = len(leads)
        if L == 0:
            QMessageBox.warning(self, "Aucun chef de table", "Sélectionnez au moins un chef de table.")
            return
        T = L

        cap_min = max(5, self.cap_min.value())
        cap_max = min(10, max(cap_min, self.cap_max.value()))
        R = max(0, N - L)
        target_k = int(round(R / max(1, T) + 1))
        k = max(cap_min, min(cap_max, target_k))
        rot_per_table = max(1, k - 1)

        rule = "exclusivity" if self.chk_exclusivity.isChecked() else "coverage"

        # Budget utilisable (temps total - pauses)
        total_minutes_budget = max(0, int((info["date_end"] - info["date_start"]).total_seconds() // 60))
        pauses = (info["pause_count"] or 0) * (info["pause_minutes"] or 0)
        budget = max(0, total_minutes_budget - pauses)
        trans = max(2, min(5, self.trans.value() or 2))

        # borne Social Golfer approx
        if k >= 3 and R > 1:
            r_sg = (R - 1) // (k - 2)
        else:
            r_sg = 1

        # exclusivité : S minimal sous contraintes (max durée)
        # couverture : S assez grand pour donner au max de rotatifs une tournée complète
        if rule == "exclusivity":
            S_min = max(1, ceil(R / (T * rot_per_table))) if R > 0 else 1
            S = max(1, min(r_sg, T, S_min))
        else:  # coverage
            S_need = max(1, ceil(R / (T * rot_per_table))) if R > 0 else 1
            S = max(1, min(r_sg, T, S_need))

        # Durée max qui rentre
        dur = max(8, floor((budget - S * trans) / S)) if S > 0 else 10
        if dur <= 0:
            S = 1
            dur = max(5, budget - trans)

        # Applique
        self.num_tables.setValue(T)
        self.cap_min.setValue(cap_min); self.cap_max.setValue(cap_max)
        self.session_count.setValue(S)
        self.dur.setValue(dur); self.trans.setValue(trans)
        self._apply_sessions()
        self._update_info()
        QMessageBox.information(self, "Paramètres proposés",
            f"Tables (chefs): {T} | Capacité ≈ {k} (min-max {cap_min}-{cap_max})\n"
            f"Sessions: {S} × ({dur}+{trans} min) | Règle: {'Exclusivité' if rule=='exclusivity' else 'Couverture'}"
        )
