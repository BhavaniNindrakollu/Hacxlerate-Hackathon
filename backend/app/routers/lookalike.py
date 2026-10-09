"""Look-alike Lab endpoints: generate variants and cross-reference with monitored data."""

import json
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Detection, User
from app.security import ANALYST_PLUS, require_roles
from app.services.lookalike import generate_variants
from app.services.normalize import normalize_name

router = APIRouter(prefix="/lookalike", tags=["lookalike"])


class LookalikeRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)


@router.post("/generate")
def generate_lookalikes(
    payload: LookalikeRequest,
    user: User = Depends(require_roles(*ANALYST_PLUS)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Generate typos, swaps, homoglyphs, spacing, added-words and check monitored data."""
    brand_name = payload.name.strip()
    variants = generate_variants(brand_name)

    # Collect monitored candidate identifiers from DB
    detections = db.scalars(select(Detection)).all()
    monitored_map: dict[str, dict[str, Any]] = {}

    for d in detections:
        try:
            cand = json.loads(d.candidate_json)
        except Exception:
            continue

        cand_name = cand.get("name") or cand.get("title") or ""
        cand_handle = cand.get("handle") or cand.get("package_id") or ""

        match_info = {
            "detection_id": d.id,
            "verdict": d.verdict,
            "score": d.score,
            "candidate_type": d.candidate_type,
            "platform": cand.get("platform") or cand.get("store") or "N/A",
            "name": cand_name,
            "handle": cand_handle,
        }

        # Index normalized forms
        norm_name = normalize_name(cand_name)
        norm_handle = normalize_name(cand_handle)
        if norm_name:
            monitored_map[norm_name] = match_info
        if norm_handle:
            monitored_map[norm_handle] = match_info

    annotated_variants = []
    matches_found = 0

    for v in variants:
        v_str = v["variant"]
        v_norm = normalize_name(v_str)

        match = monitored_map.get(v_norm)
        # Also check substring match if added-word
        if not match:
            for k, info in monitored_map.items():
                if v_norm == k or (len(v_norm) >= 5 and v_norm in k):
                    match = info
                    break

        exists = match is not None
        if exists:
            matches_found += 1

        annotated_variants.append(
            {
                "variant": v_str,
                "technique": v["technique"],
                "exists_in_monitored": exists,
                "matched_candidate": match,
            }
        )

    return {
        "brand_name": brand_name,
        "total_variants": len(annotated_variants),
        "matches_found": matches_found,
        "variants": annotated_variants,
    }
