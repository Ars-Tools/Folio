#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cron table — scheduled agent tasks."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class Cron(SQLModel, table=True):
    __tablename__ = "crons"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent: str = Field(
        sa_column=sa.Column(sa.String, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
    )
    name: str = Field(default="")
    schedule: str                       # JSON: {"cron":"..."} and/or {"at":["...",...]}
    message: str
    fired: Optional[str] = Field(default=None)   # ISO8601 UTC — last fire time
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
