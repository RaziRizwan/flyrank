"""
auth.py -- the one guard. Password hashing (bcrypt, direct -- passlib's bcrypt backend is
broken against current bcrypt releases, confirmed while building this) and JWT
issuance/verification live here and nowhere else.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import repository

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60 * 24  # 24h -- fine for a capstone; a refresh flow is a stretch goal

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: int, tenant_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRY_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


class CurrentUser:
    def __init__(self, user_id: int, tenant_id: int, email: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.email = email


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> CurrentUser:
    """The one reusable guard every authenticated route depends on. Requests without
    valid auth are rejected here, before any route body runs."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                             detail={"error": "Access token required"})
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                             detail={"error": "Invalid or expired token"})

    user = repository.get_user_by_id(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                             detail={"error": "Invalid or expired token"})
    return CurrentUser(user_id=user["id"], tenant_id=user["tenant_id"], email=user["email"])
