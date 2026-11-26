"""F1 accounts: register, login, current user."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session, select

from app.auth import create_access_token, get_current_user
from app.db import get_session
from app.models import User
from app.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)
    role: Literal["student", "faculty", "researcher"] = "student"   # admins are not self-registered
    department: Optional[str] = None


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    department: Optional[str] = None
    bio: Optional[str] = None
    links: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


def to_out(user: User) -> UserOut:
    return UserOut(
        id=str(user.id), name=user.name, email=user.email, role=user.role,
        department=user.department, bio=user.bio, links=user.links,
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, session: Session = Depends(get_session)):
    email = data.email.lower()
    if session.exec(select(User).where(User.email == email)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "email_taken", "message": "An account with this email already exists."},
        )
    user = User(
        name=data.name, email=email, password_hash=hash_password(data.password),
        role=data.role, department=data.department,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return TokenOut(access_token=create_access_token(user), user=to_out(user))


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """Form fields: username = email, password. (Form format so /docs 'Authorize' works.)"""
    user = session.exec(select(User).where(User.email == form.username.lower())).first()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "bad_credentials", "message": "Wrong email or password."},
        )
    return TokenOut(access_token=create_access_token(user), user=to_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return to_out(user)


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: ChangePasswordIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Change the authenticated member's password after verifying the current one."""
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_current_password", "message": "Current password is incorrect."},
        )
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "same_password", "message": "Choose a new password different from the current one."},
        )
    user.password_hash = hash_password(data.new_password)
    session.add(user)
    session.commit()
