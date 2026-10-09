"""Detection detail, export, and history-management endpoints."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import DELETE_HISTORY_CONFIRMATION, get_settings
from app.db import get_db
from app.models import Brand, Detection, OfficialAsset, ScanRun, User
from app.routers.brand import _to_brand_out
from app.routers.social import _format_detection
from app.schemas import DeleteHistoryIn
from app.security import (
    ADMIN_ONLY,
    ANALYST_PLUS,
    get_current_user,
    require_roles,
    write_audit,
)

router = APIRouter(prefix="/detections", tags=["detections"])

# SQLite INTEGER is 64-bit; larger path IDs would raise OverflowError -> HTTP 500.
MAX_SQLITE_INT = 2**63 - 1


@router.get("/export")
def export_detections(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Downloadable JSON snapshot of detection history. Does not modify data."""
    detections = db.scalars(select(Detection).order_by(Detection.id)).all()
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by": user.email,
        "count": len(detections),
        "items": [_format_detection(d) for d in detections],
    }
    return payload


@router.get("/{detection_id}")
def get_detection(
    detection_id: int = PathParam(..., le=MAX_SQLITE_INT),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    d = db.get(Detection, detection_id)
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection with ID {detection_id} not found.",
        )

    formatted = _format_detection(d)

    brand = db.scalar(select(Brand).order_by(Brand.id.desc()))
    brand_data = None
    if brand:
        b_out = _to_brand_out(brand)
        brand_data = b_out.model_dump()
        brand_data["logo_path"] = brand.logo_path

    formatted["brand"] = brand_data
    return formatted


@router.delete("/history")
def delete_detection_history(
    payload: DeleteHistoryIn,
    request: Request,
    user: User = Depends(require_roles(*ADMIN_ONLY)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete scan runs and detections only. Brand profiles, logos, users, and allowlists are kept."""
    if payload.confirmation.strip() != DELETE_HISTORY_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Confirmation phrase mismatch. Type {DELETE_HISTORY_CONFIRMATION} exactly to proceed. "
                "This action deletes detection records and scan runs only."
            ),
        )

    detection_count = db.scalar(select(func.count()).select_from(Detection)) or 0
    scan_count = db.scalar(select(func.count()).select_from(ScanRun)) or 0
    brand_count = db.scalar(select(func.count()).select_from(Brand)) or 0
    asset_count = db.scalar(select(func.count()).select_from(OfficialAsset)) or 0

    backup_files: list[str] = []
    if payload.create_backup:
        backup_files = _backup_before_delete(db)

    try:
        db.query(Detection).delete()
        db.query(ScanRun).delete()
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deletion failed. The database was rolled back and no records were removed.",
        )

    remaining_brands = db.scalar(select(func.count()).select_from(Brand)) or 0
    remaining_assets = db.scalar(select(func.count()).select_from(OfficialAsset)) or 0
    remaining_users = db.scalar(select(func.count()).select_from(User)) or 0
    if remaining_brands != brand_count or remaining_assets != asset_count:
        write_audit(db, user, "delete_history_integrity_warning", "", request)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Integrity check failed after deletion. Restore from the backup file.",
        )

    write_audit(
        db,
        user,
        "delete_detection_history",
        f"detections={detection_count} scans={scan_count}",
        request,
    )
    return {
        "status": "ok",
        "message": (
            f"Deleted {detection_count} detection records and {scan_count} scan runs. "
            "Brand profiles, official assets, uploaded logos, and user accounts were not changed."
        ),
        "deleted_detections": detection_count,
        "deleted_scan_runs": scan_count,
        "remaining_brands": remaining_brands,
        "remaining_official_assets": remaining_assets,
        "remaining_users": remaining_users,
        "backups": backup_files,
    }


@router.delete("/{detection_id}")
def delete_detection(
    request: Request,
    detection_id: int = PathParam(..., le=MAX_SQLITE_INT),
    user: User = Depends(require_roles(*ANALYST_PLUS)),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    d = db.get(Detection, detection_id)
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection with ID {detection_id} not found.",
        )

    db.delete(d)
    db.commit()
    write_audit(db, user, "delete_detection", f"id={detection_id}", request)
    return {"status": "ok", "message": f"Detection {detection_id} deleted"}


def _backup_before_delete(db: Session) -> list[str]:
    settings = get_settings()
    settings.backup_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    created: list[str] = []

    detections = db.scalars(select(Detection).order_by(Detection.id)).all()
    export_path = settings.backup_path / f"detections_export_{stamp}.json"
    export_path.write_text(
        json.dumps(
            {
                "exported_at": stamp,
                "count": len(detections),
                "items": [_format_detection(d) for d in detections],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    created.append(str(export_path.name))

    sqlite_file = settings.sqlite_file
    if sqlite_file and sqlite_file.exists():
        dest = settings.backup_path / f"impostorradar_before_history_delete_{stamp}.db"
        src = sqlite3.connect(str(sqlite_file))
        try:
            dst = sqlite3.connect(str(dest))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        created.append(str(Path(dest).name))
    return created
