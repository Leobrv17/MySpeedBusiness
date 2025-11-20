from __future__ import annotations

import re
from typing import List

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTextEdit, QVBoxLayout


class BulkAddDialog(QDialog):
    """Dialog simple pour coller plusieurs participants en une fois."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajout en masse")

        layout = QVBoxLayout(self)

        instructions = QLabel(
            "Collez une ligne par participant (séparateur ; , ou tabulation) :\n"
            "Prénom;Nom;Métier;Visiteur(Oui/Non);Chef de table(Oui/Non)",
            self,
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.text = QTextEdit(self)
        self.text.setPlaceholderText(
            "Exemple :\n"
            "Alice;Durand;Coach business;Non;Oui\n"
            "Bob;Martin;Architecte;Oui;Non"
        )
        layout.addWidget(self.text)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_rows(self) -> List[dict]:
        rows: List[dict] = []
        for line in self.text.toPlainText().splitlines():
            if not line.strip():
                continue
            parts = [p.strip() for p in re.split(r"[;,\t]", line)]
            if len(parts) < 3:
                continue
            first, last, job, *rest = parts
            is_guest = self._to_bool(rest[0]) if len(rest) >= 1 else False
            is_lead = self._to_bool(rest[1]) if len(rest) >= 2 else False
            rows.append(
                {
                    "first_name": first,
                    "last_name": last,
                    "job": job,
                    "is_guest": is_guest,
                    "is_table_lead": is_lead,
                }
            )
        return rows

    def _to_bool(self, value: str) -> bool:
        return value.strip().lower() in {"oui", "yes", "true", "1", "o", "y"}
