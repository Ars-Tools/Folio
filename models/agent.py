#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent table — agent configuration stored in DB."""
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class Agent(SQLModel, table=True):
    __tablename__ = "agents"

    id: str = Field(primary_key=True)
    provider: str = Field(foreign_key="providers.id")
    model: str
    name: str
    prompt: str = Field(default="")
    avatar: str = Field(default="")
    capabilities: str = Field(default="[]")
    model_params: str = Field(default="{}")
    concurrency: int = Field(default=0)
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
