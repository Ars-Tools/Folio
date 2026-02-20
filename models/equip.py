#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Equip table — skill-to-agent assignment (many-to-many)."""
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class Equip(SQLModel, table=True):
    __tablename__ = "equips"

    skill: str = Field(
        sa_column=sa.Column(sa.String, sa.ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
    )
    agent: str = Field(
        sa_column=sa.Column(sa.String, sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    )
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
