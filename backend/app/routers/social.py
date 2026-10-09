"""Social media monitoring and scanning endpoints."""

import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.connectors.factory import get_social_connector
from app.db import get_db
from app.models import AppSetting, Brand, Detection, ScanRun, User
from app.routers.brand import _to_brand_out, seed_demo_brand
from app.security import ANALYST_PLUS, get_current_user, require_roles, write_audit
from app.services.scoring import score_candidate

router = APIRouter(tags=["social"])


def _format_detection(d: Detection) -> dict[str, Any]:
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

    return {
        "id": d.id,
        "scan_id": d.scan_id,
        "candidate_type": d.candidate_type,
        "candidate": cand,
        "score": d.score,
        "verdict": d.verdict,
        "evidence": evidence,
        "breakdown": breakdown,
        "lookalike_technique": d.lookalike_technique,
    }


def run_social_scan_internal(db: Session) -> dict[str, Any]:
    brand = db.scalar(select(Brand).order_by(Brand.id.desc()))
    if not brand:
        seed_demo_brand(db)
        brand = db.scalar(select(Brand).order_by(Brand.id.desc()))

    brand_out = _to_brand_out(brand)
    brand_dict = brand_out.model_dump()
    brand_dict["logo_path"] = brand.logo_path

    sim_setting = db.scalar(
        select(AppSetting).where(AppSetting.key == "simulate_social_unavailable")
    )
    is_sim_unavailable = bool(sim_setting and sim_setting.enabled)

    connector = get_social_connector()
    conn_result = connector.fetch()

    source_status = "unavailable" if (is_sim_unavailable or conn_result.status == "unavailable") else "ok"
    source_message = (
        conn_result.message
        if source_status == "unavailable" and conn_result.message
        else ("source unavailable, showing cached/sample data" if source_status == "unavailable" else None)
    )

    items = list(conn_result.items or [])

    scan_run = ScanRun(
        brand_id=brand.id,
        scan_type="social",
        source_name=getattr(connector, "name", "social_sample"),
        source_status=source_status,
        source_message=source_message,
    )
    db.add(scan_run)
    db.flush()

    detections_out = []
    for candidate in items:
        scoring_res = score_candidate(brand_dict, candidate)

        detection = Detection(
            scan_id=scan_run.id,
            candidate_type="social",
            candidate_json=json.dumps(candidate),
            score=scoring_res["score"],
            verdict=scoring_res["verdict"],
            evidence_json=json.dumps(scoring_res["evidence"]),
            breakdown_json=json.dumps(scoring_res["breakdown"]),
            lookalike_technique=scoring_res.get("lookalike_technique"),
        )
        db.add(detection)
        db.flush()
        detections_out.append(_format_detection(detection))

    db.commit()

    return {
        "scan_id": scan_run.id,
        "source_status": source_status,
        "source_message": source_message,
        "total_scanned": len(detections_out),
        "threats_count": sum(1 for d in detections_out if d["verdict"] in {"High", "Medium", "Low"}),
        "detections": detections_out,
    }


@router.post("/scan/social")
def run_social_scan(
    request: Request,
    user: User = Depends(require_roles(*ANALYST_PLUS)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Execute social monitoring scan against the shared brand profile. Adds detections; does not wipe history."""
    result = run_social_scan_internal(db)
    write_audit(db, user, "scan_social", f"scanned={result['total_scanned']}", request)
    return result


@router.get("/detections/social")
def list_social_detections(
    verdict: str | None = Query(None),
    platform: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = select(Detection).where(Detection.candidate_type == "social").order_by(desc(Detection.score))

    if verdict:
        query = query.where(Detection.verdict == verdict)

    detections = db.scalars(query.limit(limit)).all()
    results = []

    for d in detections:
        formatted = _format_detection(d)
        cand = formatted["candidate"]

        if platform and cand.get("platform", "").lower() != platform.lower():
            continue

        if search:
            q = search.lower()
            haystack = f"{cand.get('name', '')} {cand.get('handle', '')} {cand.get('bio', '')}".lower()
            if q not in haystack:
                continue

        results.append(formatted)

    latest_run = db.scalar(
        select(ScanRun).where(ScanRun.scan_type == "social").order_by(desc(ScanRun.id))
    )

    return {
        "source_status": latest_run.source_status if latest_run else "ok",
        "source_message": latest_run.source_message if latest_run else None,
        "count": len(results),
        "items": results,
    }
