#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auth API — login validates a user token and issues JWT."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DBSession
import jwt
from datetime import datetime, timedelta, timezone

from core.auth import SECRET_KEY, ALGORITHM
from core.db import get_db
from models.auth import AuthRequest
from models.token import Token, TokenKind

router = APIRouter()

@router.post("/auth/login")
def login(request: AuthRequest, db: DBSession = Depends(get_db)):
    # Look up the token in DB — must exist and be kind=user
    row = db.get(Token, request.token)
    if not row or row.kind != TokenKind.user:
        raise HTTPException(status_code=401, detail="Invalid token")

    payload = {
        "sub": row.name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    jwt_str = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": jwt_str, "token_type": "bearer", "name": row.name}