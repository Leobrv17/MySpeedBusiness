from __future__ import annotations

from datetime import datetime  # ✅ AJOUT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from msb.infra.db import Base


class EventORM(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # ✅
    date_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)    # ✅

    # paramètres d’organisation
    num_tables: Mapped[int] = mapped_column(Integer, default=0)
    table_capacity_min: Mapped[int] = mapped_column(Integer, default=6)
    table_capacity_max: Mapped[int] = mapped_column(Integer, default=10)
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    session_duration_minutes: Mapped[int] = mapped_column(Integer, default=10)
    transition_minutes: Mapped[int] = mapped_column(Integer, default=2)

    rule_priority: Mapped[str] = mapped_column(String(20), default="exclusivity")  # "exclusivity" ou "coverage"
    pause_count: Mapped[int] = mapped_column(Integer, default=0)
    pause_minutes: Mapped[int] = mapped_column(Integer, default=0)

    participants: Mapped[list["ParticipantORM"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    seatings: Mapped[list["SeatingORM"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class ParticipantORM(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    job: Mapped[str] = mapped_column(String(200), nullable=False)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=False)
    is_table_lead: Mapped[bool] = mapped_column(Boolean, default=False)

    event: Mapped["EventORM"] = relationship(back_populates="participants")

    __table_args__ = (
        UniqueConstraint("event_id", "first_name", "last_name", "job", name="uq_participant_identity"),
    )


class SeatingORM(Base):
    __tablename__ = "seatings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    session_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 0..S-1
    table_index: Mapped[int] = mapped_column(Integer, nullable=False)    # 0..T-1
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), nullable=False, index=True)

    event: Mapped["EventORM"] = relationship(back_populates="seatings")
