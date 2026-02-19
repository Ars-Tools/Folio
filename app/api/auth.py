from fastapi import APIRouter, Depends, HTTPException
import jwt
from datetime import datetime, timedelta

from ..core.auth import SECRET_KEY, ALGORITHM
from ..schema.auth import AuthRequest

router = APIRouter()

@router.post("/auth/login")
def login(request: AuthRequest):
    if request.user == "admin" and request.password == "admin123":
        payload = {
            "sub": request.user,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")