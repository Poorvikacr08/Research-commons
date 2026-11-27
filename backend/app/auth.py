"""
Login tokens (JWT) and "who is logged in" dependencies.

How it works:
  1. POST /api/auth/login checks email + password and returns a token.
  2. The front end sends it on every request:  Authorization: Bearer <token>
  3. A route adds `user: User = Depends(get_current_user)` and FastAPI
     gives it the logged-in user (or replies 401 if the token is missing/bad).

Dependencies for other routers:
  get_current_user           -> must be logged in
  get_current_user_optional  -> user or None (e.g. public search)
  require_admin              -> must be logged in AND role == "admin"
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.config import load_jwt_secret
from app.db import get_session
from app.models import User

JWT_SECRET = load_jwt_secret()
JWT_ALGORITHM = "HS256"
TOKEN_HOURS = 24

# tokenUrl makes the "Authorize" button work in /docs
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _user_from_token(token: Optional[str], session: Session) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
    return session.get(User, user_id)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    user = _user_from_token(token, session)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "not_authenticated", "message": "Please log in."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> Optional[User]:
    return _user_from_token(token, session)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Admins only."},
        )
    return user
