#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Approval table — human-in-the-loop tool approval."""
from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    denied = "denied"


class Approval(SQLModel, table=True):
    __tablename__ = "approvals"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent: str = Field(foreign_key="agents.id")
    request: str
    status: ApprovalStatus = Field(default=ApprovalStatus.pending)
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
