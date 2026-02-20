#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tokens API — CRUD for token management."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select
from typing import Optional
from datetime import datetime, timezone
import secrets

from ..core.auth import get_current_sender
from ..core.db import get_db
from ..models.token import Token, TokenKind

router = APIRouter()


@router.get("/tokens", dependencies=[Depends(get_current_sender)])
async def list_tokens(db: DBSession = Depends(get_db)):
    rows = db.exec(select(Token)).all()
    return {"tokens": [{
        "id": r.id[:12] + "..." if len(r.id) > 16 else r.id,
        "full_id": r.id,
        "name": r.name,
        "kind": r.kind.value,
        "update": r.update.isoformat(),
    } for r in rows]}


@router.get("/token/{token_id:path}", dependencies=[Depends(get_current_sender)])
async def get_token(token_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Token, token_id)
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"id": row.id, "name": row.name, "kind": row.kind.value, "update": row.update.isoformat()}


class TokenCreate(BaseModel):
    name: str
    kind: str = "node"


@router.post("/tokens", dependencies=[Depends(get_current_sender)])
async def create_token(data: TokenCreate, db: DBSession = Depends(get_db)):
    try:
        kind = TokenKind(data.kind)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid kind: {data.kind}")
    token_id = f"fol_{secrets.token_urlsafe(32)}"
    row = Token(id=token_id, name=data.name, kind=kind)
    db.add(row)
    db.commit()
    return {"status": "ok", "id": row.id}


@router.delete("/token/{token_id:path}", dependencies=[Depends(get_current_sender)])
async def delete_token(token_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Token, token_id)
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    db.delete(row)
    db.commit()
    return {"status": "ok"}
