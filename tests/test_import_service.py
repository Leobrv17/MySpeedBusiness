from datetime import datetime, timedelta
from pathlib import Path
import sys

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from msb.services.import_service import ImportService
from msb.services.persistence import Persistence


def _make_event(tmp_path):
    persistence = Persistence()
    db_path = tmp_path / "event.db"
    now = datetime.now()
    persistence.new_event(db_path, "Event", now, now + timedelta(hours=1))
    return persistence


def test_import_excel_respects_boolean_columns(tmp_path):
    persistence = _make_event(tmp_path)
    importer = ImportService(persistence)

    excel_path = tmp_path / "participants.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Prénom", "Nom", "Métier", "Visiteur (Oui/Non)", "Chef de table (Oui/Non)"])
    ws.append(["Alice", "Doe", "Développeuse", "Oui", "Non"])
    ws.append(["Bob", "Smith", "Coach", "Non", "Oui"])
    wb.save(excel_path)

    added = importer.import_from_excel(excel_path)
    participants = persistence.list_participants()

    assert added == 2
    assert any(p.first_name == "Alice" and p.is_guest and not p.is_table_lead for p in participants)
    assert any(p.first_name == "Bob" and p.is_table_lead and not p.is_guest for p in participants)


def test_import_excel_booleans_are_case_insensitive(tmp_path):
    persistence = _make_event(tmp_path)
    importer = ImportService(persistence)

    excel_path = tmp_path / "participants.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Prénom", "Nom", "Métier", "Visiteur", "Chef de table"])
    ws.append(["Claire", "Durand", "Développeuse", "OUI", "Non"])
    ws.append(["Denis", "Martin", "Coach", "o", "N"])
    wb.save(excel_path)

    added = importer.import_from_excel(excel_path)
    participants = persistence.list_participants()

    assert added == 2
    assert any(p.first_name == "Claire" and p.is_guest and not p.is_table_lead for p in participants)
    assert any(p.first_name == "Denis" and p.is_guest and not p.is_table_lead for p in participants)
