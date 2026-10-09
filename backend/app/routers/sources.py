"""Settings and source status management endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import AppSetting, User
from app.schemas import SourceStatus, SourcesOut, SourceToggleIn
from app.security import ADMIN_ONLY, get_current_user, require_roles, write_audit

router = APIRouter(prefix="/sources", tags=["sources"])


def _get_setting_bool(db: Session, key: str, default: bool = False) -> bool:
    row = db.scalar(select(AppSetting).where(AppSetting.key == key))
    if not row:
        return default
    return bool(row.enabled)


def _set_setting_bool(db: Session, key: str, enabled: bool) -> None:
    row = db.scalar(select(AppSetting).where(AppSetting.key == key))
    if not row:
        row = AppSetting(key=key, enabled=enabled)
        db.add(row)
    else:
        row.enabled = enabled
    db.commit()


@router.get("", response_model=SourcesOut)
def get_sources_status(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SourcesOut:
    sim_social = _get_setting_bool(db, "simulate_social_unavailable", False)
    sim_apps = _get_setting_bool(db, "simulate_apps_unavailable", False)
    mode = get_settings().connector_mode

    social_status = (
        SourceStatus(
            name="Social Monitoring API",
            status="unavailable",
            message="source unavailable, showing cached/sample data (simulated)",
            using_cached=True,
        )
        if sim_social
        else SourceStatus(
            name="Social Monitoring API",
            status="ok",
            message=(
                "Using bundled sample social candidates (no live social API is connected)"
                if mode != "live"
                else "Live social connector requested — falls back to sample data if the API is unavailable"
            ),
            using_cached=mode != "live",
        )
    )

    apps_status = (
        SourceStatus(
            name="App Stores API",
            status="unavailable",
            message="source unavailable, showing cached/sample data (simulated)",
            using_cached=True,
        )
        if sim_apps
        else SourceStatus(
            name="App Stores API",
            status="ok",
            message=(
                "Using bundled sample app-store candidates (no live store API is connected)"
                if mode != "live"
                else "Live app-store connector requested — falls back to sample data if the API is unavailable"
            ),
            using_cached=mode != "live",
        )
    )

    return SourcesOut(
        social=social_status,
        apps=apps_status,
        simulate_social_unavailable=sim_social,
        simulate_apps_unavailable=sim_apps,
        connector_mode=mode,
    )


@router.post("/toggle", response_model=SourcesOut)
def toggle_sources(
    payload: SourceToggleIn,
    request: Request,
    user: User = Depends(require_roles(*ADMIN_ONLY)),
    db: Session = Depends(get_db),
) -> SourcesOut:
    if payload.simulate_social_unavailable is not None:
        _set_setting_bool(
            db, "simulate_social_unavailable", payload.simulate_social_unavailable
        )
    if payload.simulate_apps_unavailable is not None:
        _set_setting_bool(
            db, "simulate_apps_unavailable", payload.simulate_apps_unavailable
        )
    write_audit(db, user, "toggle_sources", payload.model_dump_json(), request)
    return get_sources_status(user, db)
