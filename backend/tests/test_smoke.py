from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "ImpostorRadar"


def test_connectors_never_raise() -> None:
    from app.connectors.appstore_sample import AppStoreSampleConnector
    from app.connectors.live_connector import LiveAppStoreConnector, LiveSocialConnector
    from app.connectors.social_sample import SocialSampleConnector

    for connector in (
        SocialSampleConnector(),
        AppStoreSampleConnector(),
        LiveSocialConnector(),
        LiveAppStoreConnector(),
    ):
        result = connector.fetch()
        assert result.status in ("ok", "unavailable")
        assert isinstance(result.items, list)


def test_seed_uploads_are_copied_to_fresh_upload_dir(tmp_path) -> None:
    from app.main import ensure_seed_uploads

    ensure_seed_uploads(tmp_path)
    names = {p.name for p in tmp_path.glob("*.png")}
    assert {"paytm_official.png", "paytm_clone.png", "neutral_farm.png"} <= names

    # Idempotent and non-destructive: existing files are never overwritten.
    marker = tmp_path / "paytm_official.png"
    marker.write_bytes(b"user-modified")
    ensure_seed_uploads(tmp_path)
    assert marker.read_bytes() == b"user-modified"
