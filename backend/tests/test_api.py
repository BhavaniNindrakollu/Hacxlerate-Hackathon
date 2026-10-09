"""Integration tests for ImpostorRadar REST API endpoints (authenticated)."""


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_brand_validation_error(admin):
    """Brand profile validation: empty name, invalid platform/handle/store are rejected."""
    res = admin.post("/api/brand", json={"company_name": "", "keywords": []})
    assert res.status_code == 422

    res_plat = admin.post(
        "/api/brand",
        json={
            "company_name": "TestCorp",
            "social_accounts": [{"platform": "myspace", "handle": "testcorp"}],
        },
    )
    assert res_plat.status_code == 422

    res_handle = admin.post(
        "/api/brand",
        json={
            "company_name": "TestCorp",
            "social_accounts": [{"platform": "twitter", "handle": "bad handle!!"}],
        },
    )
    assert res_handle.status_code == 422

    res_store = admin.post(
        "/api/brand",
        json={
            "company_name": "TestCorp",
            "official_apps": [
                {"store": "f-droid", "package_id": "com.test", "developer_name": "Test Inc"}
            ],
        },
    )
    assert res_store.status_code == 422


def test_load_demo_brand(admin):
    """Load demo brand endpoint populates Paytm profile."""
    res = admin.post("/api/brand/demo")
    assert res.status_code == 200
    data = res.json()
    assert data["company_name"] == "Paytm"
    assert len(data["social_accounts"]) >= 3
    assert len(data["official_apps"]) >= 2
    assert "wallet" in data["keywords"]
    assert data["is_demo"] is True


def test_demo_brand_requires_confirmation_when_custom_brand_exists(admin):
    """Custom brand is protected from accidental demo overwrite."""
    res = admin.post("/api/brand", json={"company_name": "KampusVC", "keywords": ["jobs"]})
    assert res.status_code == 200

    blocked = admin.post("/api/brand/demo")
    assert blocked.status_code == 409

    ok = admin.post("/api/brand/demo?confirm_overwrite=true")
    assert ok.status_code == 200
    assert ok.json()["company_name"] == "Paytm"


def test_social_scan_and_listing(admin):
    """Execute social scan and fetch detections."""
    admin.post("/api/brand/demo")

    res_scan = admin.post("/api/scan/social")
    assert res_scan.status_code == 200
    scan_data = res_scan.json()
    assert scan_data["total_scanned"] > 0
    assert scan_data["source_status"] == "ok"

    res_list = admin.get("/api/detections/social")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["count"] > 0
    assert list_data["source_status"] == "ok"


def test_official_social_accounts_excluded_from_scoring(admin):
    """Official allowlisted handles must score zero with an explicit exclusion reason."""
    admin.post("/api/brand/demo")
    admin.post("/api/scan/social")

    items = admin.get("/api/detections/social", params={"limit": 500}).json()["items"]
    officials = [
        d
        for d in items
        if (d["candidate"].get("handle") or "").lower() in {"paytm", "paytmofficial"}
    ]
    assert officials, "sample dataset must include the official handles"

    for det in officials:
        assert det["score"] == 0
        assert det["verdict"] == "Safe"
        assert any("Official verified brand asset" in ev for ev in det["evidence"])


def test_apps_scan_and_listing(admin):
    """Execute apps scan and fetch detections."""
    admin.post("/api/brand/demo")

    res_scan = admin.post("/api/scan/apps")
    assert res_scan.status_code == 200
    scan_data = res_scan.json()
    assert scan_data["total_scanned"] > 0
    assert scan_data["source_status"] == "ok"

    res_list = admin.get("/api/detections/apps")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["count"] > 0


def test_official_apps_excluded_from_scoring(admin):
    """Official package IDs / developers from the allowlist must never be scored as threats."""
    admin.post("/api/brand/demo")
    admin.post("/api/scan/apps")

    items = admin.get("/api/detections/apps", params={"limit": 500}).json()["items"]
    officials = [
        d
        for d in items
        if (d["candidate"].get("package_id") or "").lower()
        in {"net.one97.paytm", "com.paytm.business", "id473941634"}
    ]
    assert officials, "sample dataset must include the official packages"

    for det in officials:
        assert det["score"] == 0
        assert det["verdict"] == "Safe"
        assert any("Official verified brand asset" in ev for ev in det["evidence"])


def test_lookalike_lab_api(analyst):
    """Look-alike Lab API returns generated variants."""
    res = analyst.post("/api/lookalike/generate", json={"name": "Paytm"})
    assert res.status_code == 200
    data = res.json()
    assert data["brand_name"] == "Paytm"
    assert data["total_variants"] > 10
    assert len(data["variants"]) > 0


def test_sources_toggle_resilience(admin, analyst):
    """Check resilience toggle for simulating unavailable sources."""
    res_toggle = admin.post(
        "/api/sources/toggle", json={"simulate_social_unavailable": True}
    )
    assert res_toggle.status_code == 200
    body = res_toggle.json()
    assert body["simulate_social_unavailable"] is True
    assert body["social"]["status"] == "unavailable"

    res_denied = analyst.post(
        "/api/sources/toggle", json={"simulate_social_unavailable": False}
    )
    assert res_denied.status_code == 403

    res_scan = admin.post("/api/scan/social")
    assert res_scan.status_code == 200
    assert res_scan.json()["source_status"] == "unavailable"
    assert "cached/sample" in res_scan.json()["source_message"]

    res_back = admin.post(
        "/api/sources/toggle", json={"simulate_social_unavailable": False}
    )
    assert res_back.status_code == 200
    assert res_back.json()["simulate_social_unavailable"] is False


def test_dashboard_stats(viewer, admin):
    """Trust Radar Dashboard metrics endpoint (read-only role can view)."""
    admin.post("/api/brand/demo")
    admin.post("/api/scan/social")

    res = viewer.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert "brand_exposure_score" in data
    assert "severity_counts" in data
    assert "platforms" in data
    assert "techniques" in data


def test_detection_detail_and_takedown_pack(admin):
    """Detection detail, takedown text, and takedown PDF work for analysts+."""
    admin.post("/api/brand/demo")
    admin.post("/api/scan/social")

    items = admin.get("/api/detections/social", params={"limit": 500}).json()["items"]
    threats = [d for d in items if d["verdict"] in {"High", "Medium", "Low"}]
    assert threats, "sample dataset must produce at least one threat"

    det_id = threats[0]["id"]

    detail = admin.get(f"/api/detections/{det_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["id"] == det_id
    assert detail_body["brand"]["company_name"] == "Paytm"

    res_text = admin.get(f"/api/takedown/{det_id}/text")
    assert res_text.status_code == 200
    assert len(res_text.json()["text"]) > 100

    res_pdf = admin.get(f"/api/takedown/{det_id}/pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert len(res_pdf.content) > 1000


def test_export_detections(admin):
    """JSON export snapshot contains the full detection history."""
    admin.post("/api/brand/demo")
    admin.post("/api/scan/social")

    res = admin.get("/api/detections/export")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] > 0
    assert len(body["items"]) == body["count"]
    assert body["exported_by"] == admin.user["email"]


def test_oversized_path_ids_return_422_not_500(admin):
    """IDs larger than SQLite's 64-bit INTEGER must be rejected by validation, never crash."""
    big = 99999999999999999999  # > 2**63 - 1
    assert admin.get(f"/api/detections/{big}").status_code == 422
    assert admin.get(f"/api/takedown/{big}/text").status_code == 422
    assert admin.get(f"/api/takedown/{big}/pdf").status_code == 422
    assert admin.patch(f"/api/users/{big}", json={"role": "viewer"}).status_code == 422
    assert admin.delete(f"/api/detections/{big}").status_code == 422


def test_valid_out_of_range_id_still_404(admin):
    """In-range but nonexistent IDs keep their 404 semantics."""
    assert admin.get("/api/detections/999999").status_code == 404
    assert admin.get("/api/detections/-1").status_code == 404


def test_upload_serving_headers_block_script_execution(admin):
    """Served uploads carry sandbox CSP + nosniff so uploaded SVG/HTML cannot execute scripts."""
    res = admin.get("/uploads/paytm_official.png")
    assert res.status_code == 200
    assert res.headers.get("content-security-policy") == "sandbox"
    assert res.headers.get("x-content-type-options") == "nosniff"
