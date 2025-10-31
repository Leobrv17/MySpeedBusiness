from __future__ import annotations
from PySide6.QtWidgets import QWidget, QFormLayout, QSpinBox, QLabel, QVBoxLayout
from msb.services.persistence import Persistence

class SessionsPage(QWidget):
    def __init__(self, persistence: Persistence, on_changed):
        super().__init__()
        self.p = persistence
        self.on_changed = on_changed
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.session_count = QSpinBox(self); self.session_count.setRange(0, 100)
        self.session_dur = QSpinBox(self); self.session_dur.setRange(1, 240); self.session_dur.setValue(10)
        self.transition = QSpinBox(self); self.transition.setRange(0, 60); self.transition.setValue(2)
        form.addRow("Nombre de sessions", self.session_count)
        form.addRow("Durée (minutes) / session", self.session_dur)
        form.addRow("Transition (minutes)", self.transition)
        layout.addLayout(form)
        self.info = QLabel("", self); layout.addWidget(self.info)

        self.session_count.valueChanged.connect(self.apply)
        self.session_dur.valueChanged.connect(self.apply)
        self.transition.valueChanged.connect(self.apply)

    def load_from_event(self):
        try:
            info = self.p.get_event_info()
        except RuntimeError:
            self.session_count.setValue(0); self.session_dur.setValue(10); self.transition.setValue(2); self.info.setText(""); return
        self.session_count.setValue(info["session_count"] or 0)
        self.session_dur.setValue(info["dur"] or 10)
        self.transition.setValue(info["trans"] or 2)
        self._update_info()

    def apply(self):
        try:
            self.p.update_event_params(
                session_count=self.session_count.value(),
                dur=self.session_dur.value(),
                trans=self.transition.value(),
            )
        except RuntimeError:
            return
        self._update_info()
        if self.on_changed: self.on_changed()

    def _update_info(self):
        try:
            info = self.p.get_event_info()
        except RuntimeError:
            self.info.setText(""); return
        total = (info["session_count"] or 0) * ((info["dur"] or 0) + (info["trans"] or 0))
        self.info.setText(f"Temps total (incl. transitions) ≈ {total} min")
