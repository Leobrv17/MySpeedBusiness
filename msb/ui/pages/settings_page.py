from __future__ import annotations
from dataclasses import dataclass
from math import ceil
from PySide6.QtCore import QDateTime, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QDateTimeEdit, QSpinBox, QMessageBox
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

        # ---------- Priorité ----------
        self.rule_info = QLabel(
            "Priorité appliquée : exclusivité (répétitions de paires évitées autant que possible)",
            self,
        )
        self.rule_info.setWordWrap(True)
        root.addWidget(self.rule_info)

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

        self._loading = False

        self._general_timer = QTimer(self)
        self._general_timer.setSingleShot(True)
        self._general_timer.setInterval(250)
        self._general_timer.timeout.connect(self._apply_general)

        # ---------- Signals (save on change) ----------
        self.ev_name.textEdited.connect(self._schedule_apply_general)  # ✅ applique après 250ms de pause
        self.ev_name.editingFinished.connect(self._apply_general)  # ✅ filet de sécurité si on sort du champ
        self.ev_start.dateTimeChanged.connect(self._schedule_apply_general)  # ✅ idem pour la date
        self.ev_end.dateTimeChanged.connect(self._schedule_apply_general)

        for w in (self.num_tables, self.cap_min, self.cap_max, self.session_count, self.dur, self.trans):
            w.valueChanged.connect(self._apply_sessions)

        for w in (self.pause_count, self.pause_minutes):
            w.valueChanged.connect(self._apply_pauses)

    # --------- Load / Apply ----------
    def load_from_event(self):
        self._loading = True
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

        self._loading = False
        self._update_info()

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

        target_per_table = self._target_capacity(n, info["num_tables"] or 0, info["cap_min"] or 5, info["cap_max"] or 10)

        self.info.setText(
            f"Participants: {n} | Cible/table ≈ {target_per_table} | Budget utile ≈ {usable} min | "
            f"Sessions réalisables ≈ {sessions_fit} | Priorité: Exclusivité"
        )

    @staticmethod
    def _target_capacity(n: int, T: int, cap_min: int, cap_max: int) -> int:
        if T <= 0: return cap_min
        return max(cap_min, min(cap_max, ceil(n / T)))

    def auto_tune(self):
        from math import ceil

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

        # 1) Tables choisies par l'utilisateur (indépendant des chefs)
        T = max(1, self.num_tables.value())
        if T > N:
            T = N  # pas plus de tables que de personnes

        # 2) Capacité par table : on DOIT asseoir tout le monde à chaque session
        # Répartition équilibrée: certaines tables à k_hi, d'autres à k_lo, avec 5..10
        k_lo = max(5, N // T)
        k_hi = min(10, k_lo + 1) if (N % T) else k_lo
        # vérifier faisabilité: si k_lo > 10 => impossible avec T → il faut + de tables
        if k_lo > 10:
            QMessageBox.warning(self, "Capacité impossible",
                                "Avec ce nombre de tables, on dépasserait 10 places/table.\nAugmentez le nombre de tables.")
            return
        # vérif min: si k_lo < 5, on peut rester à 5 et laisser plus de tables à 5 (ok)
        # on fixera cap_min/cap_max = [5..10]
        cap_min = 5
        cap_max = max(10, k_hi) if k_hi > 10 else 10  # standard 5..10

        # 3) Sessions selon la priorité (fixée à exclusivité)
        # par session, une personne rencontre ~ (k-1) personnes de sa table
        # on approx avec k_moyen:
        k_avg = (k_lo * (T - (N % T)) + (k_lo + 1) * (N % T)) / T
        meets_per_session = max(1, int(round(k_avg - 1)))

        # Bornes SGP (approximatives) pour limiter les doublons: S <= floor((N - 1) / (k-1))
        sgp_bound = max(1, (N - 1) // max(1, meets_per_session))

        # viser "au plus 1 fois" mais discussions longues → peu de sessions, mais non triviales
        # on prend ~la moitié de la couverture théorique (rotation utile sans compresser trop la durée)
        S_target = max(1, ceil(0.5 * (N - 1) / max(1, meets_per_session)))

        # 4) Budget + durée max
        total = max(0, int((info["date_end"] - info["date_start"]).total_seconds() // 60))
        pauses = (info.get("pause_count") or 0) * (info.get("pause_minutes") or 0)
        usable = max(0, total - pauses)
        trans = max(2, min(5, self.trans.value() or 2))

        # S borné par théorie et budget; dur >= 8 min si possible
        S = max(1, min(S_target, sgp_bound))
        # ajuster S pour que la durée ne tombe pas trop bas
        while S > 1:
            dur = (usable - S * trans) // S if S else 0
            if dur >= 8:
                break
            S -= 1
        # si même S=1 est serré:
        dur = max(5, (usable - S * trans) // S if S else 10)

        # Applique UI + DB
        self.num_tables.setValue(T)
        self.cap_min.setValue(cap_min);
        self.cap_max.setValue(cap_max)
        self.session_count.setValue(S)
        self.dur.setValue(int(dur));
        self.trans.setValue(int(trans))
        self._apply_sessions()
        self._update_info()

        QMessageBox.information(
            self, "Paramètres proposés",
            f"Tables: {T} | Capacités équilibrées entre {k_lo} et {k_hi}\n"
            f"Sessions: {S} × ({dur}+{trans} min) | Priorité: Exclusivité (≤1 rencontre)"
        )

    def _schedule_apply_general(self):
        if self._loading:
            return
        self._general_timer.start()  # applique dans 250ms

    def _apply_general(self):
        if self._loading:
            return
        try:
            self.p.update_event_general(
                name=self.ev_name.text().strip(),
                date_start=self.ev_start.dateTime().toPython(),
                date_end=self.ev_end.dateTime().toPython(),
            )
        except RuntimeError:
            return
        self._update_info()
        if self.on_changed:
            self.on_changed()

