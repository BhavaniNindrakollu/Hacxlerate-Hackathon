"""Trust Radar Dashboard metrics and analytics."""

import json
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Brand, Detection, User
from app.routers.brand import _to_brand_out
from app.routers.social import _format_detection
from app.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Calculate Trust Radar metrics: severity counts, exposure score, platforms, techniques."""
    brand = db.scalar(select(Brand).order_by(Brand.id.desc()))
    brand_out = _to_brand_out(brand) if brand else None

    detections = db.scalars(select(Detection).order_by(desc(Detection.score))).all()

    total_monitored = len(detections)
    severity_counts = {"High": 0, "Medium": 0, "Low": 0, "Safe": 0}
    platform_counter: Counter[str] = Counter()
    platform_threat_counter: Counter[str] = Counter()
    technique_counter: Counter[str] = Counter()

    recent_threats = []

    for d in detections:
        verdict = d.verdict if d.verdict in severity_counts else "Safe"
        severity_counts[verdict] += 1

        try:
            cand = json.loads(d.candidate_json)
        except Exception:
            cand = {}

        plat = cand.get("platform") or cand.get("store") or d.candidate_type
        plat = plat.capitalize()
        platform_counter[plat] += 1

        is_threat = verdict in {"High", "Medium", "Low"}
        if is_threat:
            platform_threat_counter[plat] += 1

        if d.lookalike_technique:
            technique_counter[d.lookalike_technique] += 1

        if is_threat and len(recent_threats) < 6:
            recent_threats.append(_format_detection(d))

    total_threats = (
        severity_counts["High"] + severity_counts["Medium"] + severity_counts["Low"]
    )

    # Brand Exposure Score: 0–100 weighted index reflecting current threat exposure
    exposure_raw = (
        severity_counts["High"] * 12.0
        + severity_counts["Medium"] * 4.5
        + severity_counts["Low"] * 1.5
    )
    brand_exposure_score = min(100.0, round(exposure_raw, 1))

    # Platform distribution formatting for charts
    platform_data = [
        {
            "name": p,
            "total": platform_counter[p],
            "threats": platform_threat_counter[p],
        }
        for p in platform_counter
    ]

    # Technique distribution formatting for charts
    technique_data = [
        {"name": tech, "count": count}
        for tech, count in technique_counter.most_common()
    ]

    return {
        "brand": brand_out.model_dump() if brand_out else None,
        "total_monitored": total_monitored,
        "total_threats": total_threats,
        "brand_exposure_score": brand_exposure_score,
        "severity_counts": severity_counts,
        "platforms": platform_data,
        "techniques": technique_data,
        "recent_threats": recent_threats,
    }
