#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Journal table — agent-authored diary entries."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Journal(SQLModel, table=True):
    __tablename__ = "journals"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent: str = Field(foreign_key="agents.id")
    abstract: Optional[str] = Field(default=None)
    body: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
