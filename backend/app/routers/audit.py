from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import AuditLog, User
from app.security import ADMIN_ONLY, require_roles

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(
    admin: User = Depends(require_roles(*ADMIN_ONLY)),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.scalars(select(AuditLog).order_by(desc(AuditLog.id)).limit(100)).all()
    return {
        "items": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "action": row.action,
                "detail": row.detail,
                "ip_address": row.ip_address,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }
