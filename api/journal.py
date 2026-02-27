#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Memo API — agent-scoped memory slots with pin/unpin support."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select, col
from typing import Optional
from datetime import datetime, timezone

from core.auth import get_current_sender
from core.db import get_db
from models.session import Sender
from models.agent import Agent as AgentRow
from models.journal import Journal

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MemoCreate(BaseModel):
    abstract: Optional[str] = None
    body: str


class MemoUpdate(BaseModel):
    abstract: Optional[str] = None
    body: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _memo_dict(j: Journal) -> dict:
    return {
        "id": j.id,
        "agent": j.agent,
        "abstract": j.abstract,
        "body": j.body,
        "pinned": j.pinned,
        "timestamp": j.timestamp.isoformat() + "Z",
        "update": j.update.isoformat() + "Z",
    }


def _require_agent(agent_id: str, db: DBSession) -> AgentRow:
    row = db.get(AgentRow, agent_id)
    if not row:
        raise HTTPException(status_code=404, detail="Agent not found")
    return row


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post("/agent/{agent_id}/memo")
async def create_memo(
    agent_id: str,
    body: MemoCreate,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Create a new memory slot for an agent."""
    _require_agent(agent_id, db)
    entry = Journal(agent=agent_id, body=body.body, abstract=body.abstract)
    db.add(entry)
    db.flush()
    db.commit()
    return _memo_dict(entry)


@router.get("/agent/{agent_id}/memo")
async def list_memos(
    agent_id: str,
    limit: int = 50,
    before: Optional[int] = None,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """List all memos (newest first, cursor pagination)."""
    _require_agent(agent_id, db)
    stmt = select(Journal).where(Journal.agent == agent_id)
    if before is not None:
        stmt = stmt.where(col(Journal.id) < before)
    stmt = stmt.order_by(col(Journal.id).desc()).limit(limit)
    entries = db.exec(stmt).all()
    return {"entries": [_memo_dict(e) for e in entries], "has_more": len(entries) == limit}


@router.get("/agent/{agent_id}/memo/pinned")
async def pinned_memos(
    agent_id: str,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Return all pinned memo abstracts + count of unpinned (for system prompt)."""
    _require_agent(agent_id, db)
    pinned = db.exec(
        select(Journal)
        .where(Journal.agent == agent_id, Journal.pinned == True)
        .order_by(col(Journal.id).desc())
    ).all()
    total_ids = db.exec(
        select(Journal.id).where(Journal.agent == agent_id)
    ).all()
    unpinned_count = len(total_ids) - len(pinned)
    return {
        "pinned": [{"id": e.id, "abstract": e.abstract or ""} for e in pinned],
        "unpinned_count": unpinned_count,
    }


@router.get("/agent/{agent_id}/memo/search")
async def search_memos(
    agent_id: str,
    q: str = "",
    limit: int = 20,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Search memos by keyword (LIKE match on abstract and body)."""
    _require_agent(agent_id, db)
    stmt = select(Journal).where(Journal.agent == agent_id)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            (Journal.body.like(pattern))
            | (Journal.abstract.like(pattern))  # type: ignore[union-attr]
        )
    stmt = stmt.order_by(col(Journal.id).desc()).limit(min(limit, 50))
    entries = db.exec(stmt).all()
    return {
        "entries": [
            {"id": e.id, "abstract": e.abstract or "", "pinned": e.pinned}
            for e in entries
        ]
    }


@router.get("/agent/{agent_id}/memo/{memo_id}")
async def read_memo(
    agent_id: str,
    memo_id: int,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Read a single memo in full."""
    _require_agent(agent_id, db)
    entry = db.get(Journal, memo_id)
    if not entry or entry.agent != agent_id:
        raise HTTPException(status_code=404, detail="Memo not found")
    return _memo_dict(entry)


@router.put("/agent/{agent_id}/memo/{memo_id}")
async def rewrite_memo(
    agent_id: str,
    memo_id: int,
    body: MemoUpdate,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Rewrite a memo's abstract and/or body."""
    _require_agent(agent_id, db)
    entry = db.get(Journal, memo_id)
    if not entry or entry.agent != agent_id:
        raise HTTPException(status_code=404, detail="Memo not found")
    if body.abstract is not None:
        entry.abstract = body.abstract
    if body.body is not None:
        entry.body = body.body
    entry.update = datetime.now(timezone.utc)
    db.add(entry)
    db.flush()
    db.commit()
    return _memo_dict(entry)


@router.delete("/agent/{agent_id}/memo/{memo_id}")
async def forget_memo(
    agent_id: str,
    memo_id: int,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Permanently delete a memo."""
    _require_agent(agent_id, db)
    entry = db.get(Journal, memo_id)
    if not entry or entry.agent != agent_id:
        raise HTTPException(status_code=404, detail="Memo not found")
    db.delete(entry)
    db.commit()
    return {"status": "ok"}


@router.patch("/agent/{agent_id}/memo/{memo_id}/pin")
async def pin_memo(
    agent_id: str,
    memo_id: int,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Pin a memo — its abstract will be injected into the agent's context."""
    _require_agent(agent_id, db)
    entry = db.get(Journal, memo_id)
    if not entry or entry.agent != agent_id:
        raise HTTPException(status_code=404, detail="Memo not found")
    entry.pinned = True
    entry.update = datetime.now(timezone.utc)
    db.add(entry)
    db.flush()
    db.commit()
    return _memo_dict(entry)


@router.patch("/agent/{agent_id}/memo/{memo_id}/unpin")
async def unpin_memo(
    agent_id: str,
    memo_id: int,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Unpin a memo — remains in storage but won't appear in context."""
    _require_agent(agent_id, db)
    entry = db.get(Journal, memo_id)
    if not entry or entry.agent != agent_id:
        raise HTTPException(status_code=404, detail="Memo not found")
    entry.pinned = False
    entry.update = datetime.now(timezone.utc)
    db.add(entry)
    db.flush()
    db.commit()
    return _memo_dict(entry)
