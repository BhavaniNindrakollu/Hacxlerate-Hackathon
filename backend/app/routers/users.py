"""Administrator user-management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import ROLES
from app.db import get_db
from app.models import User
from app.schemas import RoleUpdateIn
from app.security import ADMIN_ONLY, require_roles, user_public, write_audit

router = APIRouter(prefix="/users", tags=["users"])

# SQLite INTEGER is 64-bit; larger path IDs would raise OverflowError -> HTTP 500.
MAX_SQLITE_INT = 2**63 - 1


@router.get("")
def list_users(
    admin: User = Depends(require_roles(*ADMIN_ONLY)),
    db: Session = Depends(get_db),
) -> dict:
    users = db.scalars(select(User).order_by(User.id)).all()
    return {"items": [user_public(u) for u in users]}


@router.patch("/{user_id}")
def update_user(
    payload: RoleUpdateIn,
    request: Request,
    admin: User = Depends(require_roles(*ADMIN_ONLY)),
    db: Session = Depends(get_db),
    user_id: int = Path(..., le=MAX_SQLITE_INT),
) -> dict:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    role = (payload.role or "").strip().lower()
    if role not in ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Role must be one of: {', '.join(ROLES)}",
        )

    admin_count = db.scalar(select(func.count()).select_from(User).where(User.role == "administrator", User.is_active.is_(True))) or 0
    becoming_non_admin = role != "administrator" or payload.is_active is False
    if target.role == "administrator" and becoming_non_admin and admin_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove or disable the last administrator.",
        )

    target.role = role
    if payload.is_active is not None:
        target.is_active = payload.is_active
    db.commit()
    db.refresh(target)
    write_audit(
        db,
        admin,
        "user_role_update",
        f"user_id={target.id} role={target.role} active={target.is_active}",
        request,
    )
    return user_public(target)
