"""Signup, login, logout, and current-user endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User
from app.schemas import LoginIn, SignupIn
from app.security import (
    clear_session_cookies,
    create_session,
    get_current_user,
    hash_password,
    set_session_cookies,
    user_public,
    validate_email,
    validate_password,
    verify_password,
    write_audit,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup(payload: SignupIn, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    if not settings.allow_signup:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration is disabled. Ask an administrator to create your account.",
        )
    try:
        email = validate_email(payload.email)
        password = validate_password(payload.password, email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    role = "administrator" if user_count == 0 else settings.signup_role
    full_name = (payload.full_name or "").strip() or email.split("@")[0]

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    session = create_session(db, user)
    set_session_cookies(response, session)
    write_audit(db, user, "signup", f"role={role}", request)
    return user_public(user)


@router.post("/login")
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    try:
        email = validate_email(payload.email)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(payload.password, user.password_hash):
        write_audit(db, None, "login_failed", email, request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled. Contact an administrator.",
        )
    session = create_session(db, user)
    set_session_cookies(response, session)
    write_audit(db, user, "login", "success", request)
    return user_public(user)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    from app.config import SESSION_COOKIE
    from app.models import AuthSession

    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session = db.get(AuthSession, token)
        if session:
            db.delete(session)
            db.commit()
    clear_session_cookies(response)
    write_audit(db, user, "logout", "", request)
    return {"status": "ok"}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return user_public(user)
