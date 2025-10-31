from __future__ import annotations
from PySide6.QtWidgets import QWidget, QFormLayout, QSpinBox, QLabel, QVBoxLayout
from msb.services.persistence import Persistence

class TablesPage(QWidget):
    def __init__(self, persistence: Persistence, on_ratio_changed):
        super().__init__()
        self.p = persistence
        self.on_ratio_changed = on_ratio_changed

        v = QVBoxLayout(self)
        form = QFormLayout()
        self.num_tables = QSpinBox(self); self.num_tables.setRange(0, 200)
        self.cap_min = QSpinBox(self); self.cap_min.setRange(1, 100); self.cap_min.setValue(6)
        self.cap_max = QSpinBox(self); self.cap_max.setRange(1, 100); self.cap_max.setValue(10)
        form.addRow("Nombre de tables", self.num_tables)
        form.addRow("Capacité min/table", self.cap_min)
        form.addRow("Capacité max/table", self.cap_max)
        v.addLayout(form)
        self.lead_ratio = QLabel("Chefs de table: 0/0", self); v.addWidget(self.lead_ratio)

        self.num_tables.valueChanged.connect(self.apply)
        self.cap_min.valueChanged.connect(self.apply)
        self.cap_max.valueChanged.connect(self.apply)

    def load_from_event(self):
        try:
            info = self.p.get_event_info()
        except RuntimeError:
            self.num_tables.setValue(0); self.cap_min.setValue(6); self.cap_max.setValue(10); self.update_ratio_label_from_db(); return
        # auto suggestion si 0
        if (info["num_tables"] or 0) == 0:
            try:
                n = len(self.p.list_participants())
            except RuntimeError:
                n = 0
            guess = max(1, round(n/8)) if n>0 else 0
            self.p.update_event_params(num_tables=guess)
            info = self.p.get_event_info()
        self.num_tables.setValue(info["num_tables"] or 0)
        self.cap_min.setValue(info["cap_min"] or 6)
        self.cap_max.setValue(info["cap_max"] or 10)
        self.update_ratio_label_from_db()

    def apply(self):
        try:
            self.p.update_event_params(
                num_tables=self.num_tables.value(),
                cap_min=min(self.cap_min.value(), self.cap_max.value()),
                cap_max=max(self.cap_min.value(), self.cap_max.value()),
            )
        except RuntimeError:
            return
        self.update_ratio_label_from_db()
        if self.on_ratio_changed: self.on_ratio_changed()

    def update_ratio_label_from_db(self):
        try:
            leads, total = self.p.count_leads()
            self.lead_ratio.setText(f"Chefs de table: {leads}/{total}")
        except RuntimeError:
            self.lead_ratio.setText("Chefs de table: 0/0")
