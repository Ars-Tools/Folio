#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crons API — CRUD for scheduled agent tasks."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select
from typing import Optional
from datetime import datetime, timezone
import json

from croniter import croniter

from core.auth import get_current_sender
from core.db import get_db
from models.cron import Cron

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_schedule(schedule: dict) -> None:
    """Raise HTTPException if *schedule* is invalid."""
    if not isinstance(schedule, dict):
        raise HTTPException(status_code=400, detail="schedule must be a JSON object")
    if "cron" not in schedule and "at" not in schedule:
        raise HTTPException(status_code=400, detail='schedule must contain "cron" and/or "at"')
    if "cron" in schedule:
        try:
            croniter(schedule["cron"])
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=f"Invalid cron expression: {exc}")
    if "at" in schedule:
        if not isinstance(schedule["at"], list):
            raise HTTPException(status_code=400, detail='"at" must be a list of ISO8601 timestamps')
        for t in schedule["at"]:
            try:
                datetime.fromisoformat(t.replace("Z", "+00:00") if "Z" in t else t)
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=400, detail=f"Invalid timestamp in at list: {exc}")


def _cron_dict(row: Cron) -> dict:
    return {
        "id": row.id,
        "agent": row.agent,
        "name": row.name,
        "schedule": json.loads(row.schedule),
        "message": row.message,
        "fired": row.fired,
        "update": row.update.isoformat() if row.update else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/agent/{agent_id}/crons", dependencies=[Depends(get_current_sender)])
async def list_crons(agent_id: str, db: DBSession = Depends(get_db)):
    rows = db.exec(select(Cron).where(Cron.agent == agent_id)).all()
    return {"crons": [_cron_dict(r) for r in rows]}


@router.get("/cron/{cron_id}", dependencies=[Depends(get_current_sender)])
async def get_cron(cron_id: int, db: DBSession = Depends(get_db)):
    row = db.get(Cron, cron_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cron not found")
    return _cron_dict(row)


class CronCreate(BaseModel):
    name: str = ""
    schedule: dict           # {"cron": "...", "at": [...]}
    message: str


@router.post("/agent/{agent_id}/crons", dependencies=[Depends(get_current_sender)])
async def create_cron(agent_id: str, data: CronCreate, db: DBSession = Depends(get_db)):
    _validate_schedule(data.schedule)
    row = Cron(
        agent=agent_id,
        name=data.name,
        schedule=json.dumps(data.schedule),
        message=data.message,
    )
    db.add(row)
    db.flush()
    db.commit()
    return {"status": "ok", "id": row.id}


class CronUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[dict] = None
    message: Optional[str] = None


@router.put("/cron/{cron_id}", dependencies=[Depends(get_current_sender)])
async def update_cron(cron_id: int, data: CronUpdate, db: DBSession = Depends(get_db)):
    row = db.get(Cron, cron_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cron not found")
    if data.name is not None:
        row.name = data.name
    if data.schedule is not None:
        _validate_schedule(data.schedule)
        row.schedule = json.dumps(data.schedule)
    if data.message is not None:
        row.message = data.message
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.flush()
    db.commit()
    return {"status": "ok"}


@router.delete("/cron/{cron_id}", dependencies=[Depends(get_current_sender)])
async def delete_cron(cron_id: int, db: DBSession = Depends(get_db)):
    row = db.get(Cron, cron_id)
    if not row:
        raise HTTPException(status_code=404, detail="Cron not found")
    db.delete(row)
    db.commit()
    return {"status": "ok"}
