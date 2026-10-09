"""Data retention & destructive-action safety tests (delete-history root cause fix)."""

from contextlib import contextmanager

from app.db import get_session_factory, reset_engine
from app.models import Brand, Detection, OfficialAsset, ScanRun, User


@contextmanager
def _db():
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def _seed_scan(api):
    api.post("/api/brand/demo")
    api.post("/api/scan/social")
    api.post("/api/scan/apps")


def _snapshot(api) -> dict:
    return {
        "social": api.get("/api/detections/social", params={"limit": 500}).json()["count"],
        "apps": api.get("/api/detections/apps", params={"limit": 500}).json()["count"],
        "export": api.get("/api/detections/export").json()["count"],
        "brand": (api.get("/api/brand").json() or {}).get("company_name"),
    }


def test_restart_preserves_all_data(api_factory):
    """Simulated server restart (new process engine + lifespan) must not wipe or reseed data."""
    a = api_factory()
    a.signup("owner@example.com", "OwnerPassw0rd!1")
    _seed_scan(a)
    before = _snapshot(a)

    a.close()
    reset_engine()

    b = api_factory()
    assert b.login("owner@example.com", "OwnerPassw0rd!1").status_code == 200
    assert _snapshot(b) == before


def test_logout_preserves_all_data(api_factory):
    a = api_factory()
    a.signup("keeper@example.com", "KeeperPassw0rd!1")
    _seed_scan(a)
    before = _snapshot(a)

    a.logout()
    assert a.login("keeper@example.com", "KeeperPassw0rd!1").status_code == 200
    assert _snapshot(a) == before


def test_scans_add_history_without_deleting_existing(admin):
    admin.post("/api/brand/demo")
    admin.post("/api/scan/social")
    first = admin.get("/api/detections/social", params={"limit": 500}).json()["count"]

    admin.post("/api/scan/social")
    second = admin.get("/api/detections/social", params={"limit": 500}).json()["count"]
    assert second > first, "a second scan must add detections, not replace history"


def test_brand_update_preserves_detection_history(admin):
    _seed_scan(admin)
    before = admin.get("/api/detections/export").json()["count"]

    res = admin.post(
        "/api/brand",
        json={"company_name": "KampusVC", "keywords": ["startup", "vc"]},
    )
    assert res.status_code == 200
    assert admin.get("/api/detections/export").json()["count"] == before


def test_demo_load_preserves_existing_history_and_users(admin):
    admin.post("/api/brand", json={"company_name": "KampusVC", "keywords": []})
    admin.post("/api/scan/social")
    before = admin.get("/api/detections/export").json()["count"]

    res = admin.post("/api/brand/demo?confirm_overwrite=true")
    assert res.status_code == 200

    assert admin.get("/api/detections/export").json()["count"] == before
    assert admin.get("/api/auth/me").status_code == 200


def test_delete_history_requires_admin_role(analyst, admin):
    _seed_scan(admin)
    denied = analyst.delete(
        "/api/detections/history", json={"confirmation": "DELETE_DETECTION_HISTORY"}
    )
    assert denied.status_code == 403
    assert admin.get("/api/detections/export").json()["count"] > 0


def test_delete_history_requires_exact_confirmation_phrase(admin):
    _seed_scan(admin)
    before = admin.get("/api/detections/export").json()["count"]

    wrong = admin.delete("/api/detections/history", json={"confirmation": "yes delete it"})
    assert wrong.status_code == 400
    assert "DELETE_DETECTION_HISTORY" in wrong.json()["detail"]

    assert admin.get("/api/detections/export").json()["count"] == before


def test_delete_history_preserves_brands_assets_users_and_writes_backups(admin, isolated_env):
    _seed_scan(admin)
    with _db() as s:
        brands_before = s.query(Brand).count()
        assets_before = s.query(OfficialAsset).count()
        users_before = s.query(User).count()
    assert brands_before >= 1
    assert assets_before >= 5
    assert users_before >= 1

    logo_file = isolated_env / "uploads" / "paytm_official.png"
    assert logo_file.exists()

    res = admin.delete(
        "/api/detections/history",
        json={"confirmation": "DELETE_DETECTION_HISTORY", "create_backup": True},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["deleted_detections"] > 0
    assert body["deleted_scan_runs"] > 0
    assert body["remaining_brands"] == brands_before
    assert body["remaining_official_assets"] == assets_before
    assert body["remaining_users"] == users_before
    assert "not changed" in body["message"]

    # Only detection history is gone.
    with _db() as s:
        assert s.query(Detection).count() == 0
        assert s.query(ScanRun).count() == 0
        assert s.query(Brand).count() == brands_before
        assert s.query(OfficialAsset).count() == assets_before
        assert s.query(User).count() == users_before

    # Brand, allowlist, and logo survive and remain served via the API.
    assert admin.get("/api/brand").json()["company_name"] == "Paytm"
    assert len(admin.get("/api/brand").json()["official_apps"]) >= 2
    assert logo_file.exists()

    # Backups were written before deletion.
    backup_dir = isolated_env / "backups"
    backup_files = sorted(p.name for p in backup_dir.iterdir())
    assert any(name.startswith("detections_export_") and name.endswith(".json") for name in backup_files)
    assert any(name.endswith(".db") for name in backup_files)
    assert len(body["backups"]) >= 2


def test_delete_history_without_backup(admin):
    _seed_scan(admin)
    res = admin.delete(
        "/api/detections/history",
        json={"confirmation": "DELETE_DETECTION_HISTORY", "create_backup": False},
    )
    assert res.status_code == 200
    assert res.json()["backups"] == []


def test_delete_history_is_audited(admin):
    _seed_scan(admin)
    admin.delete(
        "/api/detections/history",
        json={"confirmation": "DELETE_DETECTION_HISTORY", "create_backup": False},
    )
    actions = [row["action"] for row in admin.get("/api/audit").json()["items"]]
    assert "delete_detection_history" in actions


def test_apps_scan_survives_simulated_source_outage(admin):
    admin.post("/api/sources/toggle", json={"simulate_apps_unavailable": True})

    res = admin.post("/api/scan/apps")
    assert res.status_code == 200
    body = res.json()
    assert body["source_status"] == "unavailable"
    assert "cached/sample" in body["source_message"]
    assert body["total_scanned"] > 0

    listing = admin.get("/api/detections/apps").json()
    assert listing["source_status"] == "unavailable"
    assert listing["count"] > 0
