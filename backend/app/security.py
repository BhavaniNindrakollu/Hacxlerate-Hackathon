"""Password hashing, session cookies, CSRF, roles, and audit helpers."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import (
    CSRF_COOKIE,
    CSRF_HEADER,
    SESSION_COOKIE,
    get_settings,
)
from app.db import get_db
from app.models import AuditLog, AuthSession, User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ANALYST_PLUS = ("administrator", "analyst")
ADMIN_ONLY = ("administrator",)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> str:
    cleaned = normalize_email(email)
    if len(cleaned) > 254 or not EMAIL_RE.match(cleaned):
        raise ValueError("Enter a valid email address")
    return cleaned


def validate_password(password: str, email: str = "") -> str:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")
    if len(password) > 128:
        raise ValueError("Password is too long")
    if email and password.lower() == email.lower():
        raise ValueError("Password cannot be the same as the email address")
    if password.strip() != password:
        raise ValueError("Password cannot start or end with spaces")
    if password.isdigit() or password.isalpha():
        raise ValueError("Password must include letters and numbers or symbols")
    return password


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def cookie_base() -> dict:
    settings = get_settings()
    return {
        "path": "/",
        "samesite": settings.cookie_samesite.lower(),
        "secure": settings.cookie_secure_flag,
        "max_age": settings.session_hours * 3600,
    }


def set_session_cookies(response: Response, session: AuthSession) -> None:
    base = cookie_base()
    response.set_cookie(SESSION_COOKIE, session.id, httponly=True, **base)
    response.set_cookie(CSRF_COOKIE, session.csrf_token, httponly=False, **base)


def clear_session_cookies(response: Response) -> None:
    base = cookie_base()
    response.delete_cookie(SESSION_COOKIE, path=base["path"], samesite=base["samesite"], secure=base["secure"])
    response.delete_cookie(CSRF_COOKIE, path=base["path"], samesite=base["samesite"], secure=base["secure"])


def create_session(db: Session, user: User) -> AuthSession:
    settings = get_settings()
    session = AuthSession(
        id=new_session_id(),
        user_id=user.id,
        csrf_token=new_csrf_token(),
        expires_at=utcnow() + timedelta(hours=settings.session_hours),
        last_seen_at=utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    if request.client:
        return request.client.host
    return None


def write_audit(db: Session, user: User | None, action: str, detail: str = "", request: Request | None = None) -> None:
    log = AuditLog(
        user_id=user.id if user else None,
        action=action,
        detail=detail[:2000],
        ip_address=client_ip(request) if request else None,
    )
    db.add(log)
    db.commit()


def _load_session(request: Request, db: Session) -> tuple[AuthSession | None, User | None]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None, None
    session = db.get(AuthSession, token)
    if not session:
        return None, None
    if session.expires_at < utcnow():
        db.delete(session)
        db.commit()
        return None, None
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        db.delete(session)
        db.commit()
        return None, None
    session.last_seen_at = utcnow()
    db.commit()
    return session, user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    session, user = _load_session(request, db)
    if not user or not session:
        expired = bool(request.cookies.get(SESSION_COOKIE))
        detail = (
            "Session expired. Please log in again."
            if expired
            else "Authentication required. Please log in."
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        header = request.headers.get(CSRF_HEADER, "")
        if not header or not secrets.compare_digest(header, session.csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed. Reload the page and try again.",
            )
    return user


def require_roles(*roles: str):
    allowed = set(roles)

    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user

    return dependency


def enforce_csrf(request: Request, db: Session) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    session, user = _load_session(request, db)
    if not user or not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )
    header = request.headers.get(CSRF_HEADER, "")
    if not header or not secrets.compare_digest(header, session.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed. Reload the page and try again.",
        )


def user_public(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "permissions": permissions_for(user.role),
    }


def permissions_for(role: str) -> dict[str, bool]:
    is_admin = role == "administrator"
    is_analyst = role in ANALYST_PLUS
    return {
        "view": True,
        "scan": is_analyst,
        "modify_brand": is_analyst,
        "generate_takedown": is_analyst,
        "delete_detection": is_analyst,
        "delete_history": is_admin,
        "manage_sources": is_admin,
        "manage_users": is_admin,
        "view_audit": is_admin,
    }
