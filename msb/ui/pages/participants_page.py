from __future__ import annotations
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QLineEdit, QCheckBox, QMessageBox
from msb.services.persistence import Persistence

class ParticipantsModel(QAbstractTableModel):
    COLS = ["ID", "Nom", "Prénom", "Métier", "Visiteur", "Chef de table"]

    def __init__(self, persistence: Persistence):
        super().__init__()
        self.p = persistence
        self.rows = []  # cache ORM rows

    def reload(self):
        try:
            self.rows = list(self.p.list_participants())
        except RuntimeError:
            self.rows = []
        self.layoutChanged.emit()

    def rowCount(self, parent=None): return len(self.rows)
    def columnCount(self, parent=None): return len(self.COLS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid(): return None
        r = self.rows[index.row()]
        if role in (Qt.DisplayRole, Qt.EditRole):
            c = index.column()
            if c == 0: return r.id
            if c == 1: return r.last_name
            if c == 2: return r.first_name
            if c == 3: return r.job
            if c == 4: return "Oui" if r.is_guest else "Non"
            if c == 5: return "Oui" if r.is_table_lead else "Non"
        return None

    def flags(self, index: QModelIndex):
        if index.column() == 0:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value, role=Qt.EditRole):
        if role != Qt.EditRole: return False
        r = self.rows[index.row()]
        c = index.column()
        if c == 1:
            self.p.update_participant(r.id, last_name=str(value).strip())
        elif c == 2:
            self.p.update_participant(r.id, first_name=str(value).strip())
        elif c == 3:
            self.p.update_participant(r.id, job=str(value).strip())
        elif c == 4:
            v = str(value).strip().lower() in ("oui","yes","true","1")
            self.p.update_participant(r.id, is_guest=v)
        elif c == 5:
            v = str(value).strip().lower() in ("oui","yes","true","1")
            self.p.update_participant(r.id, is_table_lead=v)
        else:
            return False
        self.reload()
        return True

class ParticipantsPage(QWidget):
    def __init__(self, persistence: Persistence, on_ratio_changed):
        super().__init__()
        self.p = persistence
        self.on_ratio_changed = on_ratio_changed

        v = QVBoxLayout(self)
        h = QHBoxLayout()
        self.in_first = QLineEdit(self); self.in_first.setPlaceholderText("Prénom")
        self.in_last = QLineEdit(self); self.in_last.setPlaceholderText("Nom")
        self.in_job = QLineEdit(self); self.in_job.setPlaceholderText("Métier")
        self.chk_guest = QCheckBox("Visiteur", self)
        self.chk_lead = QCheckBox("Chef de table", self)
        btn_add = QPushButton("Ajouter", self); btn_add.clicked.connect(self.add_clicked)
        for w in (self.in_first, self.in_last, self.in_job, self.chk_guest, self.chk_lead, btn_add):
            h.addWidget(w)
        v.addLayout(h)

        self.model = ParticipantsModel(self.p)
        self.table = QTableView(self); self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        v.addWidget(self.table)

        h2 = QHBoxLayout()
        btn_del = QPushButton("Supprimer la sélection", self)
        btn_del.clicked.connect(self.delete_selected)
        h2.addStretch(1); h2.addWidget(btn_del)
        v.addLayout(h2)

    def reload(self):
        self.model.reload()

    def add_clicked(self):
        first = self.in_first.text().strip()
        last = self.in_last.text().strip()
        job = self.in_job.text().strip()
        if not first or not last or not job:
            QMessageBox.warning(self, "Champs requis", "Prénom, Nom et Métier sont obligatoires."); return
        try:
            self.p.add_participant(first, last, job, self.chk_guest.isChecked(), self.chk_lead.isChecked())
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e)); return
        self.in_first.clear(); self.in_last.clear(); self.in_job.clear()
        self.chk_guest.setChecked(False); self.chk_lead.setChecked(False)
        self.reload()
        if self.on_ratio_changed: self.on_ratio_changed()

    def delete_selected(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel: return
        ids = [ self.model.index(r.row(), 0).data() for r in sel ]
        for pid in ids:
            self.p.remove_participant(int(pid))
        self.reload()
        if self.on_ratio_changed: self.on_ratio_changed()
