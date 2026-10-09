"""App store monitoring and scanning endpoints."""

import json
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.connectors.factory import get_app_connector
from app.db import get_db
from app.models import AppSetting, Brand, Detection, ScanRun, User
from app.routers.brand import _to_brand_out, seed_demo_brand
from app.routers.sources import _get_setting_bool
from app.routers.social import _format_detection
from app.security import ANALYST_PLUS, get_current_user, require_roles, write_audit
from app.services.scoring import score_candidate

router = APIRouter(tags=["apps"])


def run_apps_scan_internal(db: Session) -> dict[str, Any]:
    brand = db.scalar(select(Brand).order_by(Brand.id.desc()))
    if not brand:
        seed_demo_brand(db)
        brand = db.scalar(select(Brand).order_by(Brand.id.desc()))

    brand_out = _to_brand_out(brand)
    brand_dict = brand_out.model_dump()
    brand_dict["logo_path"] = brand.logo_path

    sim_setting = db.scalar(
        select(AppSetting).where(AppSetting.key == "simulate_apps_unavailable")
    )
    is_sim_unavailable = bool(sim_setting and sim_setting.enabled)

    connector = get_app_connector()
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
        scan_type="apps",
        source_name=getattr(connector, "name", "appstore_sample"),
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
            candidate_type="app",
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


@router.post("/scan/apps")
def run_apps_scan(
    request: Request,
    user: User = Depends(require_roles(*ANALYST_PLUS)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    result = run_apps_scan_internal(db)
    write_audit(db, user, "scan_apps", f"scanned={result['total_scanned']}", request)
    return result


@router.get("/detections/apps")
def list_app_detections(
    verdict: str | None = Query(None),
    store: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = select(Detection).where(Detection.candidate_type == "app").order_by(desc(Detection.score))

    if verdict:
        query = query.where(Detection.verdict == verdict)

    detections = db.scalars(query.limit(limit)).all()
    results = []

    for d in detections:
        formatted = _format_detection(d)
        cand = formatted["candidate"]

        if store and cand.get("store", "").lower() != store.lower():
            continue

        if search:
            q = search.lower()
            haystack = (
                f"{cand.get('title', '')} {cand.get('package_id', '')} "
                f"{cand.get('developer_name', '')} {cand.get('description', '')}"
            ).lower()
            if q not in haystack:
                continue

        results.append(formatted)

    # Current availability, not the last scan's historical status — a past
    # simulated outage must not keep the "unavailable" banner up after the
    # toggle is cleared (matches GET /api/sources semantics).
    is_sim_unavailable = _get_setting_bool(db, "simulate_apps_unavailable")

    return {
        "source_status": "unavailable" if is_sim_unavailable else "ok",
        "source_message": (
            "source unavailable, showing cached/sample data (simulated)"
            if is_sim_unavailable
            else None
        ),
        "count": len(results),
        "items": results,
    }
