#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chat table — persists pydantic-ai message history per (user, agent)."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True)
    agent: str = Field(
        sa_column=sa.Column(sa.String, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True),
    )
    messages: str = Field(default="[]")
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
