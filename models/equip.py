#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Equip table — skill-to-agent assignment (many-to-many)."""
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class Equip(SQLModel, table=True):
    __tablename__ = "equips"

    skill: str = Field(foreign_key="skills.id", primary_key=True)
    agent: str = Field(foreign_key="agents.id", primary_key=True)
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
