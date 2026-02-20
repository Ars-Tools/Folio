#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chat session model — persists pydantic-ai message history per (user, agent)."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class ChatSession(SQLModel, table=True):
    """Stores the full pydantic-ai message history as JSON bytes.
    One row per (user_id, agent_id) pair."""
    __tablename__ = "chat_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    agent_id: str = Field(index=True)
    messages_json: str = Field(default="[]", description="pydantic-ai ModelMessage list serialized as JSON")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
