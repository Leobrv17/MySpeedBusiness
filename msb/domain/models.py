from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# --- Entités de base (in-memory)

@dataclass
class Participant:
    id: int
    first_name: str
    last_name: str
    job: str
    is_guest: bool = False
    is_table_lead: bool = False

    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

@dataclass
class Event:
    id: int
    name: str
    date_start: datetime
    date_end: datetime
    participants: List[Participant] = field(default_factory=list)
    num_tables: int = 0
    table_capacity_min: int = 6
    table_capacity_max: int = 10
    session_count: int = 0
    session_duration_minutes: int = 10
    transition_minutes: int = 2

@dataclass
class SeatingAssignment:
    session_index: int
    table_index: int
    participant_id: int

@dataclass
class SeatingPlan:
    event_id: int
    # plan[session][table] -> list(participant_id)
    plan: List[List[List[int]]] = field(default_factory=list)

# --- DataStore simple (remplace la DB pour l’instant)

class DataStore:
    def __init__(self) -> None:
        self._event_seq = 1
        self._participant_seq = 1
        self.current_event: Optional[Event] = None
        self.current_plan: Optional[SeatingPlan] = None

    def new_event(self, name: str, date_start: datetime, date_end: datetime) -> Event:
        evt = Event(
            id=self._event_seq,
            name=name,
            date_start=date_start,
            date_end=date_end,
            num_tables=0,
            session_count=0,
        )
        self._event_seq += 1
        self.current_event = evt
        self.current_plan = None
        return evt

    # Participants CRUD (UI)
    def add_participant(self, first_name: str, last_name: str, job: str, is_guest: bool=False, is_table_lead: bool=False) -> Participant:
        assert self.current_event, "Create event first"
        p = Participant(
            id=self._participant_seq,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            job=job.strip(),
            is_guest=is_guest,
            is_table_lead=is_table_lead,
        )
        self._participant_seq += 1
        self.current_event.participants.append(p)
        return p

    def update_participant(self, pid: int, **fields) -> None:
        assert self.current_event
        for p in self.current_event.participants:
            if p.id == pid:
                for k, v in fields.items():
                    setattr(p, k, v)
                return

    def remove_participant(self, pid: int) -> None:
        assert self.current_event
        self.current_event.participants = [p for p in self.current_event.participants if p.id != pid]

    # Helpers
    def count_leads(self) -> tuple[int, int]:
        assert self.current_event
        total_tables = self.current_event.num_tables or 0
        leads = sum(1 for p in self.current_event.participants if p.is_table_lead)
        return leads, total_tables
