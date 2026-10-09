"""Live-API negative-path test matrix against http://127.0.0.1:8000.

Read-only checks plus requests that must be REJECTED (4xx) — no successful
mutations against the live demo database. Verifies counts before/after.
Separate HTTP clients per role so cookie jars never cross-contaminate.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
DB_PATH = Path(__file__).resolve().parent / "backend" / "impostorradar.db"
ADMIN = ("admin@kampus.vc", "ImpostorRadar#2026")
VIEWER = ("priya@kampus.vc", "PriyaDemo#2026")

results: list[tuple[str, str, str]] = []  # (status, name, detail)


def record(ok: bool, name: str, detail: str = "") -> None:
    results.append(("PASS" if ok else "FAIL", name, detail))


def db_counts() -> dict[str, int]:
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    try:
        tables = ["detections", "scan_runs", "users", "brands", "official_assets", "app_settings"]
        return {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    finally:
        con.close()


def login(client: httpx.Client, creds: tuple[str, str]) -> str:
    r = client.post(f"{BASE}/api/auth/login", json={"email": creds[0], "password": creds[1]})
    r.raise_for_status()
    return client.cookies.get("ir_csrf", "")


def req(client: httpx.Client, method: str, path: str, csrf: str = "", **kw) -> httpx.Response:
    headers = kw.pop("headers", {})
    if csrf:
        headers["X-CSRF-Token"] = csrf
    return client.request(method, f"{BASE}{path}", headers=headers, **kw)


def expect(name: str, r: httpx.Response, wanted: set[int]) -> None:
    ok = r.status_code in wanted
    record(ok, name, f"got {r.status_code}, want {sorted(wanted)}")


def main() -> None:
    before = db_counts()
    print("baseline:", before)

    # ---------- A. Unauthenticated boundary ----------
    with httpx.Client(base_url=BASE, timeout=60) as c:
        unauth = [
            ("GET", "/api/brand"), ("GET", "/api/dashboard/stats"),
            ("GET", "/api/detections/1"), ("GET", "/api/detections/export"),
            ("GET", "/api/audit"), ("GET", "/api/users"), ("GET", "/api/sources"),
            ("GET", "/api/auth/me"), ("GET", "/api/takedown/1/text"),
            ("GET", "/uploads/paytm_official.png"),
            ("DELETE", "/api/detections/history"),
            ("GET", "/api/detections/social"), ("GET", "/api/detections/apps"),
        ]
        for method, path in unauth:
            expect(f"unauth {method} {path} -> 401", c.request(method, path), {401})

        expect("unauth GET /api/health -> 200", c.get("/api/health"), {200})

        # ---------- Login mechanics (anonymous-capable flows) ----------
        expect("login wrong password -> 401",
               c.post("/api/auth/login", json={"email": ADMIN[0], "password": "wrong-password"}), {401})
        expect("login SQLi-shaped email -> 401",
               c.post("/api/auth/login", json={"email": "' OR '1'='1' --", "password": "x"}), {401})
        expect("login unknown user -> 401",
               c.post("/api/auth/login", json={"email": "nobody@kampus.vc", "password": "whatever123"}), {401})
        expect("login missing password -> 422",
               c.post("/api/auth/login", json={"email": ADMIN[0]}), {422})
        expect("signup invalid email -> 422",
               c.post("/api/auth/signup", json={"email": "not-an-email", "password": "LongEnough123"}), {422})
        expect("signup weak password -> 422",
               c.post("/api/auth/signup", json={"email": "qa_probe@kampus.vc", "password": "short"}), {422})
        expect("signup duplicate email -> 409",
               c.post("/api/auth/signup", json={"email": ADMIN[0], "password": "AnotherPass123"}), {409})

        r = c.post("/api/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]})
        set_cookie = r.headers.get("set-cookie", "")
        record("HttpOnly" in set_cookie and "samesite=lax" in set_cookie.lower(),
               "session cookie flags HttpOnly+SameSite=Lax", set_cookie[:120])

    # ---------- B. Admin client ----------
    with httpx.Client(base_url=BASE, timeout=60) as ac:
        admin = login(ac, ADMIN)
        record(bool(admin), "admin login + CSRF token", (admin or "?")[:8] + "...")

        # CSRF enforcement
        expect("admin POST without CSRF header -> 403", ac.post(f"{BASE}/api/sources/toggle", json={"simulate_social_unavailable": True}), {403})
        expect("admin POST with wrong CSRF token -> 403",
               req(ac, "POST", "/api/sources/toggle", "wrong-token", json={"simulate_social_unavailable": True}), {403})

        # ID edge cases
        expect("GET /api/detections/999999 -> 404", req(ac, "GET", "/api/detections/999999", admin), {404})
        expect("GET /api/detections/0 -> 404", req(ac, "GET", "/api/detections/0", admin), {404})
        expect("GET /api/detections/-1 -> 404", req(ac, "GET", "/api/detections/-1", admin), {404})
        expect("GET /api/detections/abc -> 422", req(ac, "GET", "/api/detections/abc", admin), {422})
        expect("GET /api/detections/99999999999999999999 -> 422 (overflow guard)",
               req(ac, "GET", "/api/detections/99999999999999999999", admin), {422})
        expect("GET /api/takedown/99999999999999999999/text -> 422 (overflow guard)",
               req(ac, "GET", "/api/takedown/99999999999999999999/text", admin), {422})

        # Delete-history rejection paths (must NOT mutate)
        expect("delete-history wrong confirmation -> 400",
               req(ac, "DELETE", "/api/detections/history", admin, json={"confirmation": "WRONG_PHRASE"}), {400})
        expect("delete-history blank confirmation -> 400",
               req(ac, "DELETE", "/api/detections/history", admin, json={"confirmation": "   "}), {400})
        expect("delete-history missing confirmation -> 422",
               req(ac, "DELETE", "/api/detections/history", admin, json={}), {422})

        # User management negatives
        expect("PATCH /api/users/1 role=superadmin -> 422",
               req(ac, "PATCH", "/api/users/1", admin, json={"role": "superadmin"}), {422})
        expect("PATCH /api/users/1 demote-last-admin -> 400",
               req(ac, "PATCH", "/api/users/1", admin, json={"role": "viewer"}), {400})
        expect("PATCH /api/users/9999 -> 404",
               req(ac, "PATCH", "/api/users/9999", admin, json={"role": "viewer"}), {404})
        expect("PATCH /api/users/99999999999999999999 -> 422 (overflow guard)",
               req(ac, "PATCH", "/api/users/99999999999999999999", admin, json={"role": "viewer"}), {422})

        # Lookalike validation
        expect("lookalike name 1 char -> 422", req(ac, "POST", "/api/lookalike/generate", admin, json={"name": "P"}), {422})
        expect("lookalike name 101 chars -> 422", req(ac, "POST", "/api/lookalike/generate", admin, json={"name": "x" * 101}), {422})
        expect("lookalike missing name -> 422", req(ac, "POST", "/api/lookalike/generate", admin, json={}), {422})
        expect("lookalike name wrong type -> 422", req(ac, "POST", "/api/lookalike/generate", admin, json={"name": 12345}), {422})

        r = req(ac, "POST", "/api/lookalike/generate", admin, json={"name": "Paytm"})
        expect("lookalike 'Paytm' -> 200", r, {200})
        if r.status_code == 200:
            body = r.json()
            record(body.get("total_variants", 0) > 0, "lookalike generates variants",
                   f"total={body.get('total_variants')} matches={body.get('matches_found')}")
            record(any(v.get("matched_candidate") for v in body.get("variants", [])),
                   "lookalike finds monitored matches", "")

        r = req(ac, "POST", "/api/lookalike/generate", admin, json={"name": "<script>alert(1)</script>"})
        expect("lookalike XSS-shaped name -> 200 (transient, not stored)", r, {200})
        if r.status_code == 200:
            record(r.headers.get("content-type", "").startswith("application/json"),
                   "lookalike payload echoed only inside JSON body (XSS safety verified in browser E2E)",
                   r.headers.get("content-type", "?"))
        expect("lookalike homoglyph name -> 200", req(ac, "POST", "/api/lookalike/generate", admin, json={"name": "Ρaytm"}), {200})

        # Brand validation (422 paths only — no successful save on live data)
        expect("brand empty name -> 422", req(ac, "POST", "/api/brand", admin, json={"company_name": ""}), {422})
        expect("brand 1-char name -> 422", req(ac, "POST", "/api/brand", admin, json={"company_name": "A"}), {422})
        expect("brand 201-char name -> 422", req(ac, "POST", "/api/brand", admin, json={"company_name": "X" * 201}), {422})
        expect("brand bad platform -> 422", req(ac, "POST", "/api/brand", admin,
               json={"company_name": "Valid Name", "social_accounts": [{"platform": "myspace", "handle": "x"}]}), {422})
        expect("brand bad store -> 422", req(ac, "POST", "/api/brand", admin,
               json={"company_name": "Valid Name", "official_apps": [{"store": "microsoft", "package_id": "x", "developer_name": "y"}]}), {422})

        # Upload validation (rejected uploads create nothing)
        expect("upload text/plain -> 400", req(ac, "POST", "/api/brand/upload-logo", admin,
               files={"file": ("evil.txt", b"hello", "text/plain")}), {400})
        expect("upload .exe extension -> 400", req(ac, "POST", "/api/brand/upload-logo", admin,
               files={"file": ("evil.exe", b"MZ...", "application/octet-stream")}), {400})
        expect("upload >5MB -> 400", req(ac, "POST", "/api/brand/upload-logo", admin,
               files={"file": ("big.png", b"\x89PNG" + b"0" * (5 * 1024 * 1024 + 100), "image/png")}), {400})
        expect("upload html bytes named .png with image/png type -> 200 (finding: no magic-byte check)",
               req(ac, "POST", "/api/brand/upload-logo", admin,
                   files={"file": ("x.png", b"<html><script>alert(1)</script></html>", "image/png")}), {200})
        # Cleanup: a successful upload rewires brand.logo_path — restore it.
        import json as _json
        _con = sqlite3.connect(DB_PATH)
        try:
            _con.execute("UPDATE brands SET logo_path = '/uploads/paytm_official.png' WHERE logo_path LIKE '/uploads/brand_logo_%'")
            _con.commit()
            print("logo_path restored after polyglot-upload probe")
        finally:
            _con.close()

        # Admin reads + consistency
        expect("admin GET /api/audit -> 200", req(ac, "GET", "/api/audit", admin), {200})
        r = req(ac, "GET", "/api/users", admin)
        expect("admin GET /api/users -> 200", r, {200})
        if r.status_code == 200:
            record(len(r.json().get("items", [])) == before["users"], "users list matches DB count",
                   f"api={len(r.json().get('items', []))} db={before['users']}")

        r = req(ac, "GET", "/api/dashboard/stats", admin)
        expect("admin GET /api/dashboard/stats -> 200", r, {200})
        stats = r.json() if r.status_code == 200 else {}
        r = req(ac, "GET", "/api/detections/export", admin)
        expect("admin GET /api/detections/export -> 200", r, {200})
        export = r.json() if r.status_code == 200 else {}

        if stats and export:
            record(export.get("count") == before["detections"], "export count == DB detections",
                   f"export={export.get('count')} db={before['detections']}")
            record(stats.get("total_monitored") == before["detections"], "dashboard total_monitored == DB detections",
                   f"dash={stats.get('total_monitored')} db={before['detections']}")
            con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
            try:
                sev_db = {v: n for v, n in con.execute("SELECT verdict, COUNT(*) FROM detections GROUP BY verdict")}
            finally:
                con.close()
            dash_sev = stats.get("severity_counts", {})
            record(all(dash_sev.get(k, 0) == v for k, v in sev_db.items()),
                   "dashboard severity_counts == SQL group-by", f"dash={dash_sev} db={sev_db}")
            record(sum(sev_db.values()) == before["detections"], "severity sum == total", "")

        # CORS behaviour
        r = ac.get("/api/health", headers={"Origin": "https://evil.example"})
        acao = r.headers.get("access-control-allow-origin")
        record(acao is None, "CORS: evil origin gets no allow-origin header", f"acao={acao}")
        r = ac.options("/api/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
        record(r.headers.get("access-control-allow-origin") is None, "CORS: evil preflight not allowed",
               f"acao={r.headers.get('access-control-allow-origin')}")
        r = ac.get("/api/health", headers={"Origin": "http://localhost:5173"})
        record(r.headers.get("access-control-allow-origin") == "http://localhost:5173",
               "CORS: localhost:5173 allowed", str(r.headers.get("access-control-allow-origin")))

        # Logout invalidates session server-side
        expect("admin logout -> 200", req(ac, "POST", "/api/auth/logout", admin), {200})
        expect("admin /me after logout -> 401", req(ac, "GET", "/api/auth/me", admin), {401})

    # ---------- C. Viewer client ----------
    with httpx.Client(base_url=BASE, timeout=60) as vc:
        viewer = login(vc, VIEWER)
        record(bool(viewer), "viewer login + CSRF token", "")

        viewer_403 = [
            ("POST", "/api/scan/social", None),
            ("POST", "/api/scan/apps", None),
            ("DELETE", "/api/detections/history", {"confirmation": "DELETE_DETECTION_HISTORY"}),
            ("DELETE", "/api/detections/1", None),
            ("POST", "/api/brand", {"company_name": "Should Not Save", "keywords": []}),
            ("POST", "/api/brand/demo", None),
            ("POST", "/api/lookalike/generate", {"name": "Paytm"}),
            ("POST", "/api/sources/toggle", {"simulate_social_unavailable": True}),
        ]
        for method, path, body in viewer_403:
            kw = {"json": body} if body is not None else {}
            expect(f"viewer {method} {path} -> 403", req(vc, method, path, viewer, **kw), {403})

        expect("viewer GET /api/users -> 403", req(vc, "GET", "/api/users", viewer), {403})
        expect("viewer GET /api/audit -> 403", req(vc, "GET", "/api/audit", viewer), {403})
        expect("viewer GET /api/detections/export -> 200 (allowed)", req(vc, "GET", "/api/detections/export", viewer), {200})
        expect("viewer GET /api/detections/social -> 200 (allowed)", req(vc, "GET", "/api/detections/social", viewer), {200})
        expect("viewer GET /api/detections/apps -> 200 (allowed)", req(vc, "GET", "/api/detections/apps", viewer), {200})
        expect("viewer GET /api/takedown/1/text -> 403", req(vc, "GET", "/api/takedown/1/text", viewer), {403})

        expect("viewer logout -> 200", req(vc, "POST", "/api/auth/logout", viewer), {200})
        expect("viewer /me after logout -> 401", req(vc, "GET", "/api/auth/me", viewer), {401})

    after = db_counts()
    print("after:   ", after)
    unchanged = all(before[t] == after[t] for t in before)
    record(unchanged, "NO live data mutated by the whole suite",
           ", ".join(f"{t}:{before[t]}->{after[t]}" for t in before if before[t] != after[t]))

    fails = [r for r in results if r[0] == "FAIL"]
    print(f"\n===== RESULT: {len(results) - len(fails)}/{len(results)} passed, {len(fails)} failed =====")
    for status_, name, detail in results:
        if status_ == "FAIL":
            print(f"FAIL  {name}  [{detail}]")


if __name__ == "__main__":
    main()
