#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cron table — scheduled agent tasks."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Cron(SQLModel, table=True):
    __tablename__ = "crons"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent: str = Field(foreign_key="agents.id")
    pattern: str
    message: str
    execute: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
