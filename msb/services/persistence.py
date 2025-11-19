from __future__ import annotations
from pathlib import Path
from typing import Iterable, Optional
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, delete, func

from msb.infra.db import Base, make_engine, make_session_factory
from msb.infra.models_orm import EventORM, ParticipantORM, SeatingORM

class Persistence:
    """
    Une façade simple pour piloter la réunion courante.
    - new_event(db_path, name, start, end) → crée la BD + l'événement 1
    - open_event(db_path) → ouvre une BD existante et charge l'événement 1 (ou le dernier)
    - close_event() → ferme le contexte
    - CRUD participants
    - MAJ paramètres (tables, sessions, durées, transitions)
    - save_plan / load_plan
    """

    def __init__(self) -> None:
        self.db_path: Optional[Path] = None
        self.engine = None
        self.Session = None
        self.event_id: Optional[int] = None

    # --- utils
    def _require(self):
        if not self.Session or not self.event_id:
            raise RuntimeError("Aucune réunion ouverte")

    @contextmanager
    def session_scope(self):
        if not self.Session:
            raise RuntimeError("BD non initialisée")
        s = self.Session()
        try:
            yield s
            s.commit()
        except:
            s.rollback()
            raise
        finally:
            s.close()

    # --- lifecycle
    def new_event(self, db_path: Path, name: str, start: datetime, end: datetime):
        self.db_path = db_path
        self.engine = make_engine(db_path)
        self.Session = make_session_factory(self.engine)
        Base.metadata.create_all(self.engine)

        with self.session_scope() as s:
            evt = EventORM(name=name, date_start=start, date_end=end)
            s.add(evt)
            s.flush()
            self.event_id = evt.id
        return self.event_id

    def open_event(self, db_path: Path):
        self.db_path = db_path
        self.engine = make_engine(db_path)
        self.Session = make_session_factory(self.engine)
        # pas de create_all ici; on suppose BD déjà créée
        with self.session_scope() as s:
            evt_id = s.scalar(select(EventORM.id).order_by(EventORM.id.desc()))
            if not evt_id:
                raise RuntimeError("Aucun événement trouvé dans cette base.")
            self.event_id = evt_id
        return self.event_id

    def close_event(self):
        self.db_path = None
        self.engine = None
        self.Session = None
        self.event_id = None

    # --- lecture event & paramètres
    def get_event_info(self):
        self._require()
        with self.session_scope() as s:
            evt = s.get(EventORM, self.event_id)
            return {
                "id": evt.id,
                "name": evt.name,
                "date_start": evt.date_start,
                "date_end": evt.date_end,
                "num_tables": evt.num_tables,
                "cap_min": evt.table_capacity_min,
                "cap_max": evt.table_capacity_max,
                "session_count": evt.session_count,
                "dur": evt.session_duration_minutes,
                "trans": evt.transition_minutes,
                "pause_count": evt.pause_count or 0,
                "pause_minutes": evt.pause_minutes or 0,
            }

    def update_event_params(self, *, num_tables=None, cap_min=None, cap_max=None, session_count=None, dur=None,
                            trans=None,
                            pause_count=None, pause_minutes=None):
        self._require()
        with self.session_scope() as s:
            evt = s.get(EventORM, self.event_id)
            if num_tables is not None: evt.num_tables = int(num_tables)
            if cap_min is not None: evt.table_capacity_min = int(cap_min)
            if cap_max is not None: evt.table_capacity_max = int(cap_max)
            if session_count is not None: evt.session_count = int(session_count)
            if dur is not None: evt.session_duration_minutes = int(dur)
            if trans is not None: evt.transition_minutes = int(trans)
            if pause_count is not None: evt.pause_count = int(pause_count)
            if pause_minutes is not None: evt.pause_minutes = int(pause_minutes)

    # --- participants
    def list_participants(self):
        self._require()
        with self.session_scope() as s:
            rows = s.scalars(select(ParticipantORM).where(ParticipantORM.event_id == self.event_id).order_by(ParticipantORM.last_name, ParticipantORM.first_name)).all()
            return rows

    def add_participant(self, first_name: str, last_name: str, job: str, is_guest: bool, is_table_lead: bool):
        self._require()
        with self.session_scope() as s:
            p = ParticipantORM(
                event_id=self.event_id,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                job=job.strip(),
                is_guest=bool(is_guest),
                is_table_lead=bool(is_table_lead),
            )
            s.add(p)
            s.flush()
            return p.id

    def update_participant(self, pid: int, **fields):
        self._require()
        with self.session_scope() as s:
            p = s.get(ParticipantORM, pid)
            if not p: return
            for k, v in fields.items():
                setattr(p, k, v)

    def remove_participant(self, pid: int):
        self._require()
        with self.session_scope() as s:
            p = s.get(ParticipantORM, pid)
            if p: s.delete(p)

    def count_leads(self) -> tuple[int, int]:
        self._require()
        with self.session_scope() as s:
            leads = s.scalar(
                select(func.count())
                .select_from(ParticipantORM)
                .where(
                    ParticipantORM.event_id == self.event_id,
                    ParticipantORM.is_table_lead == True,
                )
            ) or 0
        total_tables = self.get_event_info()["num_tables"] or 0
        return leads, total_tables

    # --- plan
    def save_plan(self, plan: list[list[list[int]]]):
        """plan[session][table] = [participant_id, ...]"""
        self._require()
        with self.session_scope() as s:
            s.execute(delete(SeatingORM).where(SeatingORM.event_id == self.event_id))
            for s_idx, tables in enumerate(plan):
                for t_idx, pids in enumerate(tables):
                    for pid in pids:
                        s.add(SeatingORM(
                            event_id=self.event_id,
                            session_index=s_idx,
                            table_index=t_idx,
                            participant_id=int(pid),
                        ))

    def load_plan(self) -> list[list[list[int]]]:
        self._require()
        with self.session_scope() as s:
            rows = s.scalars(select(SeatingORM).where(SeatingORM.event_id == self.event_id)).all()
        if not rows:
            return []
        # reconstruire SxT
        S = max(r.session_index for r in rows) + 1
        T = max(r.table_index for r in rows) + 1
        plan = [[[] for _ in range(T)] for __ in range(S)]
        for r in rows:
            plan[r.session_index][r.table_index].append(r.participant_id)
        return plan

    def update_event_general(self, *, name=None, date_start=None, date_end=None):
        self._require()
        with self.session_scope() as s:
            evt = s.get(EventORM, self.event_id)
            if name is not None: evt.name = str(name).strip()
            if date_start is not None: evt.date_start = date_start
            if date_end is not None: evt.date_end = date_end