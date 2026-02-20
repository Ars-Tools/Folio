#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Token table — authentication credential registry."""
from enum import Enum
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class TokenKind(str, Enum):
    user = "user"
    node = "node"
    service = "service"


class Token(SQLModel, table=True):
    __tablename__ = "tokens"

    id: str = Field(primary_key=True)
    name: str
    kind: TokenKind = Field(default=TokenKind.user)
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
