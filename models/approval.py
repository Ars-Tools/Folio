#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Approval table — human-in-the-loop tool approval."""
from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
import sqlalchemy as sa


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    denied = "denied"


class Approval(SQLModel, table=True):
    __tablename__ = "approvals"

    id: Optional[int] = Field(default=None, primary_key=True)
    agent: str = Field(
        sa_column=sa.Column(sa.String, sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
    )
    request: str
    status: ApprovalStatus = Field(default=ApprovalStatus.pending)
    update: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
