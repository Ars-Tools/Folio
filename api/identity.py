#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Identity resolution API — look up a sender's profile by ID and category."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DBSession

from core.auth import get_current_sender
from core.db import get_db
from models.token import Token
from models.agent import Agent
from models.session import Category

router = APIRouter()


class IdentityRequest(BaseModel):
    id: str
    category: Category


class IdentityResponse(BaseModel):
    id: str
    name: str
    profile: str


@router.post("/identity/resolve", dependencies=[Depends(get_current_sender)])
def resolve_identity(
    req: IdentityRequest,
    db: DBSession = Depends(get_db),
) -> IdentityResponse:
    """Resolve a sender ID + category to their profile.

    - user / node / service → Token.profile
    - agent → Agent.profile
    """
    if req.category == Category.agent:
        row = db.get(Agent, req.id)
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        return IdentityResponse(
            id=row.id, name=row.name, profile=row.profile,
        )

    # user / node / service / system → look up token
    row = db.get(Token, req.id)
    if not row:
        raise HTTPException(status_code=404, detail="Token not found")
    return IdentityResponse(
        id=row.id, name=row.name, profile=row.profile,
    )
