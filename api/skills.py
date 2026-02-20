#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skills API — CRUD for skill master table."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select
from typing import Optional
from datetime import datetime, timezone

from core.auth import get_current_sender
from core.db import get_db
from models.skill import Skill

router = APIRouter()


@router.get("/skills", dependencies=[Depends(get_current_sender)])
async def list_skills(q: Optional[str] = None, db: DBSession = Depends(get_db)):
    stmt = select(Skill)
    if q:
        stmt = stmt.where(Skill.id.contains(q))  # type: ignore[union-attr]
    rows = db.exec(stmt).all()
    return {"skills": [{"id": r.id, "update": r.update.isoformat()} for r in rows]}


@router.get("/skill/{skill_id}", dependencies=[Depends(get_current_sender)])
async def get_skill(skill_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Skill, skill_id)
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"id": row.id, "body": row.body, "update": row.update.isoformat()}


class SkillCreate(BaseModel):
    id: str
    body: str


@router.post("/skills", dependencies=[Depends(get_current_sender)])
async def create_skill(data: SkillCreate, db: DBSession = Depends(get_db)):
    if db.get(Skill, data.id):
        raise HTTPException(status_code=409, detail="Skill already exists")
    row = Skill(id=data.id, body=data.body)
    db.add(row)
    db.commit()
    return {"status": "ok", "id": row.id}


class SkillUpdate(BaseModel):
    body: Optional[str] = None


@router.put("/skill/{skill_id}", dependencies=[Depends(get_current_sender)])
async def update_skill(skill_id: str, data: SkillUpdate, db: DBSession = Depends(get_db)):
    row = db.get(Skill, skill_id)
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    if data.body is not None:
        row.body = data.body
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    return {"status": "ok"}


@router.delete("/skill/{skill_id}", dependencies=[Depends(get_current_sender)])
async def delete_skill(skill_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Skill, skill_id)
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(row)
    db.commit()
    return {"status": "ok"}
