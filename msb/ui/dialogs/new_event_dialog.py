from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QFormLayout, QLineEdit, QDateTimeEdit
from PySide6.QtCore import QDateTime

class NewEventDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle réunion")
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit(self)
        self.start = QDateTimeEdit(self); self.start.setCalendarPopup(True); self.start.setDateTime(QDateTime.currentDateTime())
        self.end = QDateTimeEdit(self); self.end.setCalendarPopup(True); self.end.setDateTime(QDateTime.currentDateTime().addSecs(2*60*60))

        form.addRow("Nom de l'événement", self.name)
        form.addRow("Début", self.start)
        form.addRow("Fin", self.end)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_values(self):
        return self.name.text().strip(), self.start.dateTime().toPython(), self.end.dateTime().toPython()
