from __future__ import annotations
from math import floor, ceil
from dataclasses import dataclass
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QSpinBox, QLabel, QPushButton, QHBoxLayout, QMessageBox
)
from msb.services.persistence import Persistence

@dataclass
class Settings:
    num_tables: int
    cap_min: int
    cap_max: int
    session_count: int
    dur: int
    trans: int

class SettingsPage(QWidget):
    """
    Page unique pour paramétrer tables + sessions.
    - Edite: nombre de tables, capacités min/max, nb sessions, durée, transition
    - Bouton “Trouver les meilleurs paramètres automatiquement”
    """
    def __init__(self, persistence: Persistence, on_changed):
        super().__init__()
        self.p = persistence
        self.on_changed = on_changed

        self.setLayout(QVBoxLayout())
        form = QFormLayout()

        # Widgets
        self.num_tables = QSpinBox(self); self.num_tables.setRange(0, 500)
        self.cap_min = QSpinBox(self); self.cap_min.setRange(1, 100); self.cap_min.setValue(6)
        self.cap_max = QSpinBox(self); self.cap_max.setRange(1, 100); self.cap_max.setValue(10)
        self.session_count = QSpinBox(self); self.session_count.setRange(0, 500)
        self.dur = QSpinBox(self); self.dur.setRange(1, 240); self.dur.setValue(10)
        self.trans = QSpinBox(self); self.trans.setRange(0, 60); self.trans.setValue(2)

        form.addRow("Nombre de tables", self.num_tables)
        form.addRow("Capacité min/table", self.cap_min)
        form.addRow("Capacité max/table", self.cap_max)
        form.addRow("Nombre de sessions", self.session_count)
        form.addRow("Durée (minutes) / session", self.dur)
        form.addRow("Transition (minutes)", self.trans)
        self.layout().addLayout(form)

        # Infos & actions
        h = QHBoxLayout()
        self.info = QLabel("", self)
        self.btn_auto = QPushButton("Trouver les meilleurs paramètres automatiquement", self)
        self.btn_auto.clicked.connect(self.auto_tune)
        h.addWidget(self.info); h.addStretch(1); h.addWidget(self.btn_auto)
        self.layout().addLayout(h)

        # Bindings
        self.num_tables.valueChanged.connect(self.apply)
        self.cap_min.valueChanged.connect(self.apply)
        self.cap_max.valueChanged.connect(self.apply)
        self.session_count.valueChanged.connect(self.apply)
        self.dur.valueChanged.connect(self.apply)
        self.trans.valueChanged.connect(self.apply)

    # ---- Public API
    def load_from_event(self):
        """Charge les paramètres actuels depuis la DB et affiche des infos calculées."""
        try:
            info = self.p.get_event_info()
        except RuntimeError:
            self._set_widgets(Settings(0, 6, 10, 0, 10, 2))
            self._update_info()
            return

        self._set_widgets(Settings(
            num_tables=info["num_tables"] or 0,
            cap_min=info["cap_min"] or 6,
            cap_max=info["cap_max"] or 10,
            session_count=info["session_count"] or 0,
            dur=info["dur"] or 10,
            trans=info["trans"] or 2,
        ))

        # Suggestion auto si 0 tables et des participants existent
        if self.num_tables.value() == 0:
            n = len(self.p.list_participants())
            if n > 0:
                guess = max(1, round(n / 8))
                self.num_tables.setValue(guess)
                self.apply()

        self._update_info()

    def update_ratio_label_from_db(self):
        # utilisé par la status bar via main_window
        pass  # laissé vide pour compat, la status bar interroge Persistence directement

    # ---- Internals
    def _set_widgets(self, s: Settings):
        # Garantir min <= max
        cap_min = min(s.cap_min, s.cap_max)
        cap_max = max(s.cap_min, s.cap_max)

        self.num_tables.blockSignals(True)
        self.cap_min.blockSignals(True)
        self.cap_max.blockSignals(True)
        self.session_count.blockSignals(True)
        self.dur.blockSignals(True)
        self.trans.blockSignals(True)

        self.num_tables.setValue(s.num_tables)
        self.cap_min.setValue(cap_min)
        self.cap_max.setValue(cap_max)
        self.session_count.setValue(s.session_count)
        self.dur.setValue(s.dur)
        self.trans.setValue(s.trans)

        self.num_tables.blockSignals(False)
        self.cap_min.blockSignals(False)
        self.cap_max.blockSignals(False)
        self.session_count.blockSignals(False)
        self.dur.blockSignals(False)
        self.trans.blockSignals(False)

    def _read_widgets(self) -> Settings:
        cap_min = min(self.cap_min.value(), self.cap_max.value())
        cap_max = max(self.cap_min.value(), self.cap_max.value())
        return Settings(
            num_tables=self.num_tables.value(),
            cap_min=cap_min,
            cap_max=cap_max,
            session_count=self.session_count.value(),
            dur=self.dur.value(),
            trans=self.trans.value(),
        )

    def apply(self):
        """Enregistre en DB dès qu’un champ change (+ maj info)."""
        try:
            s = self._read_widgets()
            self.p.update_event_params(
                num_tables=s.num_tables,
                cap_min=s.cap_min,
                cap_max=s.cap_max,
                session_count=s.session_count,
                dur=s.dur,
                trans=s.trans,
            )
        except RuntimeError:
            return
        self._update_info()
        if self.on_changed:
            self.on_changed()

    def _update_info(self):
        """Calcule le temps total et un indicateur de ‘pression’ (participants/table)."""
        try:
            info = self.p.get_event_info()
            n = len(self.p.list_participants())
        except RuntimeError:
            self.info.setText("")
            return

        total_minutes = (info["session_count"] or 0) * ((info["dur"] or 0) + (info["trans"] or 0))
        per_table_target = self._target_capacity(n, info["num_tables"] or 0, info["cap_min"] or 6, info["cap_max"] or 10)
        self.info.setText(
            f"Participants: {n} | Cible/table ≈ {per_table_target} | Temps total ≈ {total_minutes} min"
        )

    # ---- Auto-tuning
    def auto_tune(self):
        from math import ceil, floor

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

        # Chefs & tables (1 chef/table, chefs immobiles)
        leads = [p for p in participants if p.is_table_lead]
        L = len(leads)
        if L == 0:
            QMessageBox.warning(self, "Aucun chef de table", "Sélectionnez au moins un chef de table.")
            return
        T = L  # on force l’égalité
        R = max(0, N - L)  # rotatifs

        # Capacité: k in [5..10], k inclut le chef. On cible k ~ R/T + 1 (pour équilibrer),
        # puis on borne à [5..10]
        if T == 0:
            QMessageBox.warning(self, "Configuration invalide", "Le nombre de tables doit être > 0.")
            return
        target_k = int(round(R / T + 1))  # +1 car le chef occupe une place
        k = max(5, min(10, target_k))
        rot_per_table = max(1, k - 1)

        # Borne Social Golfer pour les rotatifs (pas de pair en double) + pas de re-chef
        # r_max <= floor((R-1)/(k-2)) si k>=3; sinon prendre 1
        if k >= 3:
            r_sg = (R - 1) // (k - 2) if R > 1 else 1
        else:
            r_sg = 1
        r_max = max(1, min(T, r_sg))

        # S minimal pour offrir au moins un passage à tous (même si certains auront des byes)
        S_min = max(1, ceil(R / (T * rot_per_table))) if R > 0 else 1
        S = max(1, min(r_max, S_min))  # priorité: le minimum "cohérent" pour maximiser la durée

        # Budget & durée (on maximise la durée par session)
        budget = int((info["date_end"] - info["date_start"]).total_seconds() // 60)
        trans = max(2, min(5, self.trans.value() or 2))  # borne raisonnable
        if budget <= 0:
            # pas de budget connu → garder valeurs UI mais fixer tables & bornes
            self._set_widgets(Settings(num_tables=T, cap_min=max(2, self.cap_min.value()),
                                       cap_max=max(self.cap_max.value(), self.cap_min.value()), session_count=S,
                                       dur=self.dur.value(), trans=trans))
            self.apply()
            QMessageBox.information(self, "Paramètres proposés (sans budget)",
                                    f"Tables: {T} | k≈{k} (cap {max(2, self.cap_min.value())}-{max(self.cap_max.value(), self.cap_min.value())}) | Sessions: {S}")
            return

        # Durée max qui rentre
        if S > 0:
            dur = max(8, floor((budget - S * trans) / S))  # vise discussions longues (≥8)
        else:
            dur = 10
        if dur <= 0:
            # trop de sessions/transition pour le budget : réduire S au minimum
            S = 1
            dur = max(5, budget - trans)

        # Applique en UI + DB
        cap_min = max(5, min(self.cap_min.value(), self.cap_max.value()))
        cap_max = max(cap_min, min(10, self.cap_max.value()))
        self._set_widgets(
            Settings(num_tables=T, cap_min=cap_min, cap_max=cap_max, session_count=S, dur=dur, trans=trans))
        self.apply()

        QMessageBox.information(
            self, "Paramètres proposés",
            f"Tables (chefs): {T}  | Capacité cible/table k≈{k} (min-max {cap_min}-{cap_max})\n"
            f"Sessions: {S} × ({dur}+{trans} min) — priorité: 0 doublon, durées longues"
        )

    # ---- Helpers
    @staticmethod
    def _target_capacity(n: int, T: int, cap_min: int, cap_max: int) -> int:
        if T <= 0:
            return cap_min
        return max(cap_min, min(cap_max, ceil(n / T)))
