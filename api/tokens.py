#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tokens API — CRUD for token management."""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session as DBSession, select
from typing import Optional
from datetime import datetime, timezone
import base64
import secrets

from core.auth import get_current_sender
from core.db import get_db
from models.token import Token, TokenKind

router = APIRouter()


def _token_dict(r: Token, *, mask: bool = True) -> dict:
    tid = (r.id[:12] + "...") if mask and len(r.id) > 16 else r.id
    return {
        "id": tid,
        "full_id": r.id,
        "name": r.name,
        "kind": r.kind.value,
        "profile": r.profile,
        "hasAvatar": bool(r.avatar),
        "update": r.update.isoformat(),
    }


@router.get("/tokens", dependencies=[Depends(get_current_sender)])
async def list_tokens(db: DBSession = Depends(get_db)):
    rows = db.exec(select(Token)).all()
    return {"tokens": [_token_dict(r) for r in rows]}


@router.get("/token/{token_id}", dependencies=[Depends(get_current_sender)])
async def get_token(token_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Token, token_id)
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    return _token_dict(row, mask=False)


class TokenCreate(BaseModel):
    name: str
    kind: str = "node"
    profile: str = ""


@router.post("/tokens", dependencies=[Depends(get_current_sender)])
async def create_token(data: TokenCreate, db: DBSession = Depends(get_db)):
    try:
        kind = TokenKind(data.kind)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid kind: {data.kind}")
    token_id = f"fol_{secrets.token_urlsafe(32)}"
    row = Token(id=token_id, name=data.name, kind=kind, profile=data.profile)
    db.add(row)
    db.commit()
    return {"status": "ok", "id": row.id}


class TokenUpdate(BaseModel):
    name: Optional[str] = None
    profile: Optional[str] = None


@router.put("/token/{token_id}", dependencies=[Depends(get_current_sender)])
async def update_token(token_id: str, data: TokenUpdate, db: DBSession = Depends(get_db)):
    row = db.get(Token, token_id)
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    if data.name is not None:
        row.name = data.name
    if data.profile is not None:
        row.profile = data.profile
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.flush()
    db.commit()
    return {"status": "ok"}


@router.delete("/token/{token_id}", dependencies=[Depends(get_current_sender)])
async def delete_token(token_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Token, token_id)
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    db.delete(row)
    db.commit()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Avatar
# ---------------------------------------------------------------------------

@router.get("/token/{token_id}/avatar")
async def get_token_avatar(token_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Token, token_id)
    if not row or not row.avatar:
        raise HTTPException(status_code=404, detail="No avatar")
    if row.avatar.startswith("data:"):
        header, b64data = row.avatar.split(",", 1)
        media_type = header.split(":")[1].split(";")[0]
        return Response(content=base64.b64decode(b64data), media_type=media_type)
    return Response(content=row.avatar, media_type="image/svg+xml")


@router.put("/token/{token_id}/avatar", dependencies=[Depends(get_current_sender)])
async def upload_token_avatar(token_id: str, file: UploadFile = File(...), db: DBSession = Depends(get_db)):
    row = db.get(Token, token_id)
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    content = await file.read()
    if len(content) > 512 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 512KB)")
    media_type = file.content_type or "image/png"
    b64 = base64.b64encode(content).decode()
    row.avatar = f"data:{media_type};base64,{b64}"
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.flush()
    db.commit()
    return {"status": "ok"}


@router.delete("/token/{token_id}/avatar", dependencies=[Depends(get_current_sender)])
async def delete_token_avatar(token_id: str, db: DBSession = Depends(get_db)):
    row = db.get(Token, token_id)
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    row.avatar = ""
    row.update = datetime.now(timezone.utc)
    db.add(row)
    db.flush()
    db.commit()
    return {"status": "ok"}
