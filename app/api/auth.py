from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DBSession, select
import jwt
from datetime import datetime, timedelta

from ..core.auth import SECRET_KEY, ALGORITHM
from ..core.db import get_db
from ..models.auth import AuthRequest
from ..models.user import User

router = APIRouter()

@router.post("/auth/login")
def login(request: AuthRequest, db: DBSession = Depends(get_db)):
    user = db.exec(select(User).where(User.name == request.user)).first()
    if not user or not user.verify_password(request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    payload = {
        "sub": user.name,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}