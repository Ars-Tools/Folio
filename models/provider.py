#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provider table — LLM provider registry."""
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class Provider(SQLModel, table=True):
    __tablename__ = "providers"

    id: str = Field(primary_key=True)
    name: str
    kind: str                       # openai-chat | openai-responses | google-gla | google-vertex
    config: str = Field(default="{}") # JSON — schema depends on kind
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
