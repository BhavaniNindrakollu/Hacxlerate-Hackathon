"""Shared pytest fixtures — full test isolation from real project data.

Every test runs against a throwaway SQLite database plus temporary upload and
backup directories. The real development database (backend/impostorradar.db),
the real uploads folder, and the real backups folder are never touched.
"""

import atexit
import os
import shutil
import tempfile
from contextlib import ExitStack
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REAL_UPLOADS = BACKEND_ROOT / "uploads"

# Redirect the app to throwaway paths *before* app.* is imported anywhere,
# so even collection-time imports can never touch the real database.
_BOOTSTRAP_DIR = Path(tempfile.mkdtemp(prefix="impostorradar_test_bootstrap_"))
atexit.register(shutil.rmtree, str(_BOOTSTRAP_DIR), ignore_errors=True)

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{(_BOOTSTRAP_DIR / 'bootstrap.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(_BOOTSTRAP_DIR / "uploads")
os.environ["BACKUP_DIR"] = str(_BOOTSTRAP_DIR / "backups")
os.environ["ALLOW_SIGNUP"] = "true"
os.environ.pop("INITIAL_ADMIN_EMAIL", None)
os.environ.pop("INITIAL_ADMIN_PASSWORD", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.config import CSRF_COOKIE, CSRF_HEADER, clear_settings_cache  # noqa: E402
from app.db import get_session_factory, init_db, reset_engine  # noqa: E402
from app.main import app  # noqa: E402

ADMIN_EMAIL = "admin@impostorradar.test"
ADMIN_PASSWORD = "AdminPassw0rd!23"
ANALYST_EMAIL = "analyst@impostorradar.test"
ANALYST_PASSWORD = "AnalystPassw0rd!23"
VIEWER_EMAIL = "viewer@impostorradar.test"
VIEWER_PASSWORD = "ViewerPassw0rd!23"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


class Api:
    """TestClient wrapper that adds the CSRF header automatically."""

    def __init__(self, test_client: TestClient):
        self._client = test_client
        self.user: dict | None = None

    @property
    def test_client(self) -> TestClient:
        """Raw client for tests that intentionally bypass the CSRF helper."""
        return self._client

    def close(self) -> None:
        """Shut the client down (runs lifespan shutdown) — used to simulate a server restart."""
        self._client.__exit__(None, None, None)

    def request(self, method: str, path: str, **kwargs):
        method = method.upper()
        if method not in {"GET", "HEAD", "OPTIONS"}:
            token = self._client.cookies.get(CSRF_COOKIE)
            if token:
                headers = dict(kwargs.get("headers") or {})
                headers.setdefault(CSRF_HEADER, token)
                kwargs["headers"] = headers
        return self._client.request(method, path, **kwargs)

    def get(self, path: str, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def signup(self, email: str, password: str, full_name: str | None = None):
        body: dict = {"email": email, "password": password}
        if full_name:
            body["full_name"] = full_name
        res = self.post("/api/auth/signup", json=body)
        if res.status_code == 200:
            self.user = res.json()
        return res

    def login(self, email: str, password: str):
        res = self.post("/api/auth/login", json={"email": email, "password": password})
        if res.status_code == 200:
            self.user = res.json()
        return res

    def logout(self):
        res = self.post("/api/auth/logout")
        if res.status_code == 200:
            self.user = None
        return res

    def refresh_me(self):
        res = self.get("/api/auth/me")
        if res.status_code == 200:
            self.user = res.json()
        return res


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Point every test at a fresh database and temp upload/backup folders."""
    db_file = tmp_path / "test.db"
    uploads = tmp_path / "uploads"
    backups = tmp_path / "backups"
    uploads.mkdir()
    backups.mkdir()

    if REAL_UPLOADS.is_dir():
        for item in REAL_UPLOADS.iterdir():
            if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES:
                shutil.copy2(item, uploads / item.name)

    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("UPLOAD_DIR", str(uploads))
    monkeypatch.setenv("BACKUP_DIR", str(backups))
    monkeypatch.setenv("ALLOW_SIGNUP", "true")
    monkeypatch.delenv("INITIAL_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("INITIAL_ADMIN_PASSWORD", raising=False)

    clear_settings_cache()
    reset_engine()
    yield tmp_path
    reset_engine()
    clear_settings_cache()


@pytest.fixture
def api_factory(isolated_env):
    """Create additional API clients against the same isolated test server."""
    with ExitStack() as stack:

        def factory() -> Api:
            return Api(stack.enter_context(TestClient(app)))

        yield factory


@pytest.fixture
def client(api_factory) -> Api:
    return api_factory()


@pytest.fixture
def admin(client: Api) -> Api:
    res = client.signup(ADMIN_EMAIL, ADMIN_PASSWORD, full_name="Admin")
    assert res.status_code == 200, res.text
    assert client.user is not None and client.user["role"] == "administrator"
    return client


@pytest.fixture
def analyst(api_factory, admin) -> Api:
    c = api_factory()
    res = c.signup(ANALYST_EMAIL, ANALYST_PASSWORD, full_name="Analyst")
    assert res.status_code == 200, res.text
    assert c.user is not None and c.user["role"] == "analyst"
    return c


@pytest.fixture
def viewer(api_factory, admin, analyst) -> Api:
    c = api_factory()
    res = c.signup(VIEWER_EMAIL, VIEWER_PASSWORD, full_name="Viewer")
    assert res.status_code == 200, res.text
    assert c.user is not None and c.user["role"] == "analyst"
    upd = admin.patch(f"/api/users/{c.user['id']}", json={"role": "viewer"})
    assert upd.status_code == 200, upd.text
    c.refresh_me()
    assert c.user is not None and c.user["role"] == "viewer"
    return c


@pytest.fixture
def db_session(isolated_env):
    """Direct SQLAlchemy session against the same isolated test database."""
    init_db()
    session = get_session_factory()()
    yield session
    session.rollback()
    session.close()
