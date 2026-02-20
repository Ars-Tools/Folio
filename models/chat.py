#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chat table — persists pydantic-ai message history per (user, agent)."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True)
    agent: str = Field(foreign_key="agents.id", index=True)
    messages: str = Field(default="[]")
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
