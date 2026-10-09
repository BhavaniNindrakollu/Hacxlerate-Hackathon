"""Authentication, session, CSRF, and role-based access control tests."""

from datetime import timedelta

from app.config import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from app.models import AuthSession, User
from app.security import utcnow
from tests.conftest import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    ANALYST_EMAIL,
    ANALYST_PASSWORD,
)


def test_signup_first_user_becomes_administrator(client):
    res = client.signup("founder@example.com", "FounderPassw0rd!1", full_name="Founder")
    assert res.status_code == 200
    body = res.json()
    assert body["role"] == "administrator"
    assert body["permissions"]["manage_users"] is True
    assert body["permissions"]["delete_history"] is True
    assert "password" not in body and "password_hash" not in body


def test_signup_duplicate_email_rejected(client, admin):
    res = client.signup(ADMIN_EMAIL, "AnotherPassw0rd!1")
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"].lower()


def test_signup_validation(client):
    bad_email = client.signup("not-an-email", "ValidPassw0rd!1")
    assert bad_email.status_code == 422

    weak_password = client.signup("someone@example.com", "short")
    assert weak_password.status_code == 422

    email_as_password = client.signup("someone@example.com", "someone@example.com")
    assert email_as_password.status_code == 422


def test_self_registration_never_grants_admin(client, admin):
    res = client.signup("second@example.com", "SecondPassw0rd!1")
    assert res.status_code == 200
    assert res.json()["role"] == "analyst"


def test_login_success_invalid_and_unknown(api_factory):
    a = api_factory()
    a.signup("user1@example.com", "UserOnePassw0rd!1")

    b = api_factory()
    ok = b.login("user1@example.com", "UserOnePassw0rd!1")
    assert ok.status_code == 200
    assert b.get("/api/auth/me").status_code == 200

    wrong = api_factory().login("user1@example.com", "WrongPassw0rd!1")
    assert wrong.status_code == 401
    assert "invalid email or password" in wrong.json()["detail"].lower()

    unknown = api_factory().login("nobody@example.com", "NopePassw0rd!1")
    assert unknown.status_code == 401


def test_login_is_case_insensitive_on_email(api_factory):
    a = api_factory()
    a.signup("MiXeD@Example.com", "MixedPassw0rd!1")

    b = api_factory()
    assert b.login("mixed@example.com", "MixedPassw0rd!1").status_code == 200


def test_logout_invalidates_session(api_factory):
    a = api_factory()
    a.signup("logout@example.com", "LogoutPassw0rd!1")
    assert a.get("/api/auth/me").status_code == 200
    old_token = a.test_client.cookies.get(SESSION_COOKIE)
    assert old_token

    res = a.logout()
    assert res.status_code == 200
    assert a.get("/api/auth/me").status_code == 401

    # The old cookie value must be rejected by a different client too (server-side invalidation).
    b = api_factory()
    b.test_client.cookies.set(SESSION_COOKIE, old_token)
    assert b.get("/api/auth/me").status_code == 401


def test_logout_requires_csrf_token(api_factory):
    a = api_factory()
    a.signup("csrf@example.com", "CsrfPassw0rd!1")

    # Bypass the auto-CSRF helper: raw request without the header must be rejected.
    res = a.test_client.post("/api/auth/logout")
    assert res.status_code == 403
    assert "csrf" in res.json()["detail"].lower()


def test_state_changing_requests_require_matching_csrf_token(admin):
    res = admin.test_client.post("/api/scan/social")
    assert res.status_code == 403

    bogus = admin.post("/api/scan/social", headers={CSRF_HEADER: "bogus-token"})
    assert bogus.status_code == 403

    valid = admin.post("/api/scan/social")
    assert valid.status_code == 200


def test_csrf_cookie_is_readable_but_session_cookie_is_not(api_factory):
    c = api_factory()
    res = c.signup("cookiecheck@example.com", "CookiePassw0rd!1")

    set_cookies = res.headers.get_list("set-cookie")
    session_cookie = next(h for h in set_cookies if h.startswith(f"{SESSION_COOKIE}="))
    csrf_cookie = next(h for h in set_cookies if h.startswith(f"{CSRF_COOKIE}="))

    assert "httponly" in session_cookie.lower()
    assert "samesite=lax" in session_cookie.lower()
    assert "httponly" not in csrf_cookie.lower()


def test_unauthenticated_requests_are_rejected(client):
    for path in (
        "/api/brand",
        "/api/detections/social",
        "/api/detections/apps",
        "/api/detections/export",
        "/api/dashboard/stats",
        "/api/sources",
        "/api/users",
        "/api/audit",
    ):
        res = client.get(path)
        assert res.status_code == 401, path
        assert "authentication required" in res.json()["detail"].lower()

    assert client.post("/api/scan/social").status_code == 401


def test_expired_session_is_rejected_and_cleaned_up(admin, db_session):
    row = db_session.query(AuthSession).first()
    assert row is not None
    row.expires_at = utcnow() - timedelta(minutes=5)
    db_session.commit()

    res = admin.get("/api/auth/me")
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()
    assert db_session.query(AuthSession).count() == 0


def test_tampered_session_cookie_is_rejected(api_factory):
    a = api_factory()
    a.signup("tamper@example.com", "TamperPassw0rd!1")

    b = api_factory()
    b.test_client.cookies.set(SESSION_COOKIE, "forged-session-token-value")
    res = b.get("/api/auth/me")
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


def test_passwords_are_hashed_not_stored_plaintext(admin, db_session):
    user = db_session.query(User).filter_by(email=ADMIN_EMAIL).first()
    assert user is not None
    assert user.password_hash != ADMIN_PASSWORD
    assert user.password_hash.startswith("$2")
    assert ADMIN_PASSWORD not in user.password_hash


def test_viewer_is_read_only(viewer, admin):
    admin.post("/api/brand/demo")
    admin.post("/api/scan/social")

    # Viewer can read everything they are authorized to see.
    assert viewer.get("/api/brand").status_code == 200
    assert viewer.get("/api/detections/social").status_code == 200
    assert viewer.get("/api/detections/apps").status_code == 200
    assert viewer.get("/api/dashboard/stats").status_code == 200
    assert viewer.get("/api/sources").status_code == 200

    # Viewer cannot perform any state-changing or analyst action.
    assert viewer.post("/api/scan/social").status_code == 403
    assert viewer.post("/api/scan/apps").status_code == 403
    assert viewer.post("/api/lookalike/generate", json={"name": "Paytm"}).status_code == 403
    assert viewer.post("/api/brand", json={"company_name": "HaxCorp"}).status_code == 403
    assert viewer.post("/api/brand/demo").status_code == 403
    assert viewer.post("/api/sources/toggle", json={"simulate_social_unavailable": True}).status_code == 403
    assert viewer.get("/api/users").status_code == 403
    assert viewer.get("/api/audit").status_code == 403

    det_id = viewer.get("/api/detections/social").json()["items"][0]["id"]
    assert viewer.get(f"/api/takedown/{det_id}/text").status_code == 403
    assert viewer.get(f"/api/takedown/{det_id}/pdf").status_code == 403
    assert viewer.delete(f"/api/detections/{det_id}").status_code == 403
    assert (
        viewer.delete(
            "/api/detections/history",
            json={"confirmation": "DELETE_DETECTION_HISTORY"},
        ).status_code
        == 403
    )
    assert (
        viewer.patch(
            f"/api/users/{viewer.user['id']}", json={"role": "administrator"}
        ).status_code
        == 403
    )


def test_analyst_can_work_but_not_administer(analyst, admin):
    admin.post("/api/brand/demo")

    # Analyst capabilities.
    assert analyst.post("/api/scan/social").status_code == 200
    assert analyst.post("/api/lookalike/generate", json={"name": "Paytm"}).status_code == 200
    det_id = analyst.get("/api/detections/social").json()["items"][0]["id"]
    assert analyst.get(f"/api/takedown/{det_id}/text").status_code == 200

    # Admin-only capabilities are denied.
    assert (
        analyst.delete(
            "/api/detections/history",
            json={"confirmation": "DELETE_DETECTION_HISTORY"},
        ).status_code
        == 403
    )
    assert analyst.post("/api/sources/toggle", json={"simulate_apps_unavailable": True}).status_code == 403
    assert analyst.get("/api/users").status_code == 403
    assert analyst.get("/api/audit").status_code == 403
    assert analyst.patch(f"/api/users/{analyst.user['id']}", json={"role": "administrator"}).status_code == 403


def test_admin_can_manage_roles(admin, analyst):
    res = admin.patch(f"/api/users/{analyst.user['id']}", json={"role": "viewer"})
    assert res.status_code == 200
    assert res.json()["role"] == "viewer"

    promote = admin.patch(f"/api/users/{analyst.user['id']}", json={"role": "analyst"})
    assert promote.status_code == 200

    invalid = admin.patch(f"/api/users/{analyst.user['id']}", json={"role": "superuser"})
    assert invalid.status_code == 422

    missing = admin.patch("/api/users/99999", json={"role": "viewer"})
    assert missing.status_code == 404


def test_last_administrator_is_protected(admin):
    demote = admin.patch(f"/api/users/{admin.user['id']}", json={"role": "analyst"})
    assert demote.status_code == 400
    assert "last administrator" in demote.json()["detail"].lower()

    disable = admin.patch(
        f"/api/users/{admin.user['id']}",
        json={"role": "administrator", "is_active": False},
    )
    assert disable.status_code == 400


def test_disabled_account_session_and_login_are_blocked(admin, analyst, api_factory):
    res = admin.patch(
        f"/api/users/{analyst.user['id']}",
        json={"role": "analyst", "is_active": False},
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is False

    # Existing session is invalidated on next use.
    assert analyst.get("/api/auth/me").status_code == 401

    fresh = api_factory()
    denied = fresh.login(ANALYST_EMAIL, ANALYST_PASSWORD)
    assert denied.status_code == 403
    assert "disabled" in denied.json()["detail"].lower()


def test_audit_log_records_security_events(admin):
    admin.post("/api/brand/demo")
    admin.post("/api/scan/social")
    admin.logout()
    assert admin.login(ADMIN_EMAIL, ADMIN_PASSWORD).status_code == 200

    res = admin.get("/api/audit")
    assert res.status_code == 200
    actions = [row["action"] for row in res.json()["items"]]
    for expected in ("signup", "logout", "login", "load_demo_brand", "scan_social"):
        assert expected in actions, f"missing audit action: {expected}"

    for row in res.json()["items"]:
        assert "password" not in (row.get("detail") or "").lower()
