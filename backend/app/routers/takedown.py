"""Takedown pack API endpoints: download PDF dossier and copy-paste text."""

import json

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Brand, Detection, User
from app.routers.brand import _to_brand_out
from app.security import ANALYST_PLUS, require_roles
from app.services.takedown import build_takedown_pdf, build_takedown_text

router = APIRouter(prefix="/takedown", tags=["takedown"])

# SQLite INTEGER is 64-bit; larger path IDs would raise OverflowError -> HTTP 500.
MAX_SQLITE_INT = 2**63 - 1


def _get_det_and_brand(detection_id: int, db: Session) -> tuple[dict, dict]:
    d = db.get(Detection, detection_id)
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection {detection_id} not found.",
        )

    try:
        cand = json.loads(d.candidate_json)
    except Exception:
        cand = {}
    try:
        evidence = json.loads(d.evidence_json)
    except Exception:
        evidence = []
    try:
        breakdown = json.loads(d.breakdown_json)
    except Exception:
        breakdown = {}

    det_dict = {
        "id": d.id,
        "score": d.score,
        "verdict": d.verdict,
        "candidate_type": d.candidate_type,
        "candidate": cand,
        "evidence": evidence,
        "breakdown": breakdown,
        "lookalike_technique": d.lookalike_technique,
    }

    brand = db.scalar(select(Brand).order_by(Brand.id.desc()))
    brand_dict = {}
    if brand:
        b_out = _to_brand_out(brand)
        brand_dict = b_out.model_dump()
        brand_dict["logo_path"] = brand.logo_path

    return det_dict, brand_dict


@router.get("/{detection_id}/text")
def get_takedown_text(
    detection_id: int = Path(..., le=MAX_SQLITE_INT),
    user: User = Depends(require_roles(*ANALYST_PLUS)),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Return platform-customized takedown notice text for one-click copy."""
    det_dict, brand_dict = _get_det_and_brand(detection_id, db)
    text = build_takedown_text(det_dict, brand_dict)
    return {"text": text}


@router.get("/{detection_id}/pdf")
def get_takedown_pdf(
    detection_id: int = Path(..., le=MAX_SQLITE_INT),
    user: User = Depends(require_roles(*ANALYST_PLUS)),
    db: Session = Depends(get_db),
) -> Response:
    """Download ready-to-send takedown incident PDF dossier."""
    det_dict, brand_dict = _get_det_and_brand(detection_id, db)
    pdf_bytes = build_takedown_pdf(det_dict, brand_dict)

    filename = f"impostorradar_takedown_case_{detection_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
