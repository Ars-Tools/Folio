from fastapi import Depends, HTTPException, WebSocket, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlmodel import Session as DBSession
import jwt
import os
import secrets
import uuid

from models.session import Sender, Session, Category
from models.token import Token, TokenKind
from core.db import get_db, engine

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("ALGORITHM", "HS256")

security = HTTPBearer(auto_error=False)

def get_current_token_str(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[str]:
    if credentials:
        return credentials.credentials
    return None

def _resolve_token(token_str: str) -> Sender:
    """Resolve a Bearer token to a Sender.
    1. Try JWT decode (for web users — stateless, no DB lookup).
    2. Fall back to direct DB lookup (for node/service tokens)."""
    # Try JWT first
    try:
        payload = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id:
            return Sender(id=user_id, name=user_id, category=Category.user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        pass

    # Fall back to direct token lookup (node/service)
    with DBSession(engine) as db:
        row = db.get(Token, token_str)
        if row:
            cat = Category.user if row.kind == TokenKind.user else Category.system
            return Sender(id=row.name, name=row.name, category=cat)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_sender(
    token_str: Optional[str] = Depends(get_current_token_str)
) -> Sender:
    """Validates token and returns a Sender object."""
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _resolve_token(token_str)

# ---------------------------------------------------------------------------
# Session dependency (for agent execution context)
# ---------------------------------------------------------------------------

def get_session(sender: Sender = Depends(get_current_sender)) -> Session:
    """Build a Session from the authenticated Sender."""
    return Session(id=str(uuid.uuid4()), sender=sender)

# ---------------------------------------------------------------------------
# WebSocket authentication
# ---------------------------------------------------------------------------

async def authenticate_websocket(websocket: WebSocket) -> Sender | None:
    """Authenticate a WebSocket connection via ?token= query param.
    Returns Sender on success, or closes the socket and returns None."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    try:
        sender = _resolve_token(token)
        return sender
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
