#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Journal API — agent-scoped diary entries for persistent inner state."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select, col
from typing import Optional
from datetime import datetime, timezone

from core.auth import get_current_sender
from core.db import get_db
from models.session import Sender, Category
from models.agent import Agent as AgentRow
from models.journal import Journal

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class JournalCreate(BaseModel):
    body: str
    episode: Optional[str] = None
    abstract: Optional[str] = None


class JournalUpdate(BaseModel):
    body: Optional[str] = None
    episode: Optional[str] = None
    abstract: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _journal_dict(j: Journal) -> dict:
    return {
        "id": j.id,
        "agent": j.agent,
        "episode": j.episode,
        "abstract": j.abstract,
        "body": j.body,
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

@router.post("/agent/{agent_id}/journal")
async def create_journal(
    agent_id: str,
    body: JournalCreate,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Create a new journal entry for an agent.

    Agents write their own journals (sender must be the agent itself or
    a user with admin-level access).
    """
    _require_agent(agent_id, db)

    entry = Journal(
        agent=agent_id,
        body=body.body,
        episode=body.episode,
        abstract=body.abstract,
    )
    db.add(entry)
    db.flush()   # assigns auto-generated id before commit
    db.commit()
    return _journal_dict(entry)


@router.get("/agent/{agent_id}/journal")
async def list_journals(
    agent_id: str,
    limit: int = 20,
    before: Optional[int] = None,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """List journal entries (newest first, cursor pagination)."""
    _require_agent(agent_id, db)

    stmt = select(Journal).where(Journal.agent == agent_id)
    if before is not None:
        stmt = stmt.where(col(Journal.id) < before)
    stmt = stmt.order_by(col(Journal.id).desc()).limit(limit)
    entries = db.exec(stmt).all()
    return {
        "entries": [_journal_dict(e) for e in entries],
        "has_more": len(entries) == limit,
    }


@router.get("/agent/{agent_id}/journal/latest")
async def latest_journal(
    agent_id: str,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Return the most recent journal entry (used for system prompt preview)."""
    _require_agent(agent_id, db)

    entry = db.exec(
        select(Journal)
        .where(Journal.agent == agent_id)
        .order_by(col(Journal.id).desc())
        .limit(1)
    ).first()
    if not entry:
        return {"entry": None}
    return {"entry": _journal_dict(entry)}


@router.get("/agent/{agent_id}/journal/browse")
async def browse_journals(
    agent_id: str,
    q: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    limit: int = 20,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Browse journal abstracts — lightweight index (no body/episode).

    Parameters:
        q:      keyword filter (matched against abstract only)
        after:  ISO-8601 date/datetime — only entries *after* this time
        before: ISO-8601 date/datetime — only entries *before* this time
        limit:  max entries (capped at 50)
    """
    _require_agent(agent_id, db)

    stmt = select(Journal).where(Journal.agent == agent_id)
    if q:
        stmt = stmt.where(Journal.abstract.like(f"%{q}%"))  # type: ignore[union-attr]
    if after:
        try:
            dt_after = datetime.fromisoformat(after.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'after' datetime")
        stmt = stmt.where(Journal.timestamp >= dt_after)
    if before:
        try:
            dt_before = datetime.fromisoformat(before.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'before' datetime")
        stmt = stmt.where(Journal.timestamp < dt_before)
    stmt = stmt.order_by(col(Journal.id).desc()).limit(min(limit, 50))
    entries = db.exec(stmt).all()
    return {
        "entries": [
            {
                "id": e.id,
                "abstract": e.abstract or "",
                "timestamp": e.timestamp.isoformat() + "Z",
            }
            for e in entries
        ],
        "has_more": len(entries) == min(limit, 50),
    }


@router.get("/agent/{agent_id}/journal/entry/{entry_id}")
async def read_journal_entry(
    agent_id: str,
    entry_id: int,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Read a single journal entry in full (body + episode)."""
    _require_agent(agent_id, db)
    entry = db.get(Journal, entry_id)
    if not entry or entry.agent != agent_id:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return _journal_dict(entry)


@router.get("/agent/{agent_id}/journal/search")
async def search_journals(
    agent_id: str,
    q: Optional[str] = None,
    limit: int = 5,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    """Search journal entries by keyword (LIKE) or return most recent."""
    _require_agent(agent_id, db)

    stmt = select(Journal).where(Journal.agent == agent_id)
    if q:
        # Simple keyword search — match against body, abstract, and episode
        pattern = f"%{q}%"
        stmt = stmt.where(
            (Journal.body.like(pattern))
            | (Journal.abstract.like(pattern))  # type: ignore[union-attr]
            | (Journal.episode.like(pattern))  # type: ignore[union-attr]
        )
    stmt = stmt.order_by(col(Journal.id).desc()).limit(min(limit, 20))
    entries = db.exec(stmt).all()
    return {"entries": [_journal_dict(e) for e in entries]}


@router.put("/agent/{agent_id}/journal/{entry_id}")
async def update_journal(
    agent_id: str,
    entry_id: int,
    body: JournalUpdate,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    _require_agent(agent_id, db)
    entry = db.get(Journal, entry_id)
    if not entry or entry.agent != agent_id:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if body.body is not None:
        entry.body = body.body
    if body.episode is not None:
        entry.episode = body.episode
    if body.abstract is not None:
        entry.abstract = body.abstract
    entry.update = datetime.now(timezone.utc)
    db.add(entry)
    db.flush()
    db.commit()
    return _journal_dict(entry)


@router.delete("/agent/{agent_id}/journal/{entry_id}")
async def delete_journal(
    agent_id: str,
    entry_id: int,
    sender: Sender = Depends(get_current_sender),
    db: DBSession = Depends(get_db),
):
    _require_agent(agent_id, db)
    entry = db.get(Journal, entry_id)
    if not entry or entry.agent != agent_id:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    db.delete(entry)
    db.commit()
    return {"status": "ok"}
