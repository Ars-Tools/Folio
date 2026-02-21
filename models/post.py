#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Post table — timeline entries by agents or humans."""
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class Post(SQLModel, table=True):
    __tablename__ = "posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    sender: str = Field(index=True)  # Sender.id
    author: str
    category: str = Field(default="user")  # "agent" | "user" | "system"
    body: str  # Markdown
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
