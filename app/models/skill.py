#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill table — reusable skill definitions (SKILL.md)."""
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class Skill(SQLModel, table=True):
    __tablename__ = "skills"

    id: str = Field(primary_key=True)
    body: str
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
