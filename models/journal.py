#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Journal (memo) — agent-authored memory slots with pin support."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class Journal(SQLModel, table=True):
    __tablename__ = "journals"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent: str = Field(
        sa_column=sa.Column(sa.String, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
    )
    abstract: Optional[str] = Field(default=None)
    body: str
    pinned: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
