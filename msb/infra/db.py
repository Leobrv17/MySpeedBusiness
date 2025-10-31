from __future__ import annotations
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", echo=False, future=True)

def make_session_factory(engine):
    # 👇 clé du fix : expire_on_commit=False
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,   # ✅ objets restent “vivants” après commit
        future=True,
    )
