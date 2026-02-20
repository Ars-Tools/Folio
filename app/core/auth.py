from fastapi import Depends, HTTPException, WebSocket, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
import os
import secrets
import uuid

from app.models.session import Sender, Session, Category

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = os.getenv("ALGORITHM", "HS256")

security = HTTPBearer(auto_error=False)

def get_current_token_str(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[str]:
    if credentials:
        return credentials.credentials
    return None

def get_current_sender(
    token_str: Optional[str] = Depends(get_current_token_str)
) -> Sender:
    """
    Validates JWT and returns a Sender object.
    """
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

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

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

# ---------------------------------------------------------------------------
# Session dependency (for agent execution context)
# ---------------------------------------------------------------------------

def get_session(sender: Sender = Depends(get_current_sender)) -> Session:
    """Build a Session from the authenticated Sender. Use this as a FastAPI
    dependency wherever pydantic-ai agent execution needs `deps=Session`."""
    return Session(id=str(uuid.uuid4()), sender=sender)

# ---------------------------------------------------------------------------
# WebSocket authentication (Depends doesn't work with WS query params)
# ---------------------------------------------------------------------------

async def authenticate_websocket(websocket: WebSocket) -> Sender | None:
    """Authenticate a WebSocket connection via ?token= query param.
    Returns Sender on success, or closes the socket and returns None."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return None
        return Sender(id=user_id, name=user_id, category=Category.user)
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
