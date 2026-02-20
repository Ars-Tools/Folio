#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Approvals API — manage agent permission approvals."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select
from datetime import datetime, timezone

from ..core.auth import get_current_sender
from ..core.db import get_db
from ..models.approval import Approval, ApprovalStatus
from ..models.agent import Agent as AgentRow

router = APIRouter()


@router.get("/agent/{agent_id}/approvals", dependencies=[Depends(get_current_sender)])
async def list_approvals(agent_id: str, db: DBSession = Depends(get_db)):
    if not db.get(AgentRow, agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    rows = db.exec(select(Approval).where(Approval.agent == agent_id)).all()
    return {"approvals": [{
        "id": r.id,
        "request": r.request,
        "status": r.status.value,
        "update": r.update.isoformat(),
    } for r in rows]}


class ApprovalUpdate(BaseModel):
    status: str


@router.put("/approval/{approval_id}", dependencies=[Depends(get_current_sender)])
async def update_approval(approval_id: int, body: ApprovalUpdate, db: DBSession = Depends(get_db)):
    row = db.get(Approval, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    try:
        row.status = ApprovalStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    return {"status": "ok"}


@router.delete("/approval/{approval_id}", dependencies=[Depends(get_current_sender)])
async def delete_approval(approval_id: int, db: DBSession = Depends(get_db)):
    row = db.get(Approval, approval_id)
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    db.delete(row)
    db.commit()
    return {"status": "ok"}

