#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database initialization and session management using SQLModel + SQLite.
"""
from sqlmodel import SQLModel, Session as DBSession, create_engine
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "app.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def init_db():
    """Create all tables. Call once at app startup."""
    from ..models import (  # noqa: F401 — ensure models are registered
        Token, Provider, Agent, Chat, Approval, Cron, Journal, Skill, Equip
    )
    SQLModel.metadata.create_all(engine)


def get_db():
    """FastAPI dependency that yields a DB session."""
    with DBSession(engine) as session:
        yield session
