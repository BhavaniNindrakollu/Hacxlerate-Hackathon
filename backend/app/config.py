from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent

ROLES = ("administrator", "analyst", "viewer")
DEFAULT_SIGNUP_ROLE = "analyst"
SESSION_COOKIE = "ir_session"
CSRF_COOKIE = "ir_csrf"
CSRF_HEADER = "X-CSRF-Token"
DELETE_HISTORY_CONFIRMATION = "DELETE_DETECTION_HISTORY"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ImpostorRadar"
    environment: str = "development"
    database_url: str = "sqlite:///./impostorradar.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:5175,http://127.0.0.1:5175,http://localhost:5176,http://127.0.0.1:5176,http://localhost:8000,http://127.0.0.1:8000"
    upload_dir: str = "uploads"
    data_dir: str = "app/data"
    backup_dir: str = "backups"
    host: str = "0.0.0.0"
    port: int = 8000
    connector_mode: str = "sample"
    max_logo_bytes: int = 2 * 1024 * 1024
    session_hours: int = 12
    allow_signup: bool = True
    default_signup_role: str = DEFAULT_SIGNUP_ROLE
    # Optional first-admin bootstrap. Used only when the users table is empty.
    # Never commit real values. Leave blank to register the first user as administrator.
    initial_admin_email: str = ""
    initial_admin_password: str = ""
    cookie_secure: bool | None = None
    # "lax" is correct for same-origin deployments. Split deployments
    # (e.g. Vercel frontend -> Render backend) are cross-site, so the session
    # and CSRF cookies must be sent on API fetches: set COOKIE_SAMESITE=none
    # (requires Secure, which cookie_secure_flag enables in production).
    cookie_samesite: str = "lax"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return [o for o in origins if o != "*"]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def cookie_secure_flag(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.is_production

    @property
    def signup_role(self) -> str:
        role = (self.default_signup_role or DEFAULT_SIGNUP_ROLE).strip().lower()
        if role == "administrator":
            # Self-registration must never grant administrator by default.
            return DEFAULT_SIGNUP_ROLE
        if role not in ROLES:
            return DEFAULT_SIGNUP_ROLE
        return role

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return path

    @property
    def data_path(self) -> Path:
        path = Path(self.data_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return path

    @property
    def backup_path(self) -> Path:
        path = Path(self.backup_dir)
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        return path

    @property
    def frontend_dist(self) -> Path:
        return REPO_ROOT / "frontend" / "dist"

    @property
    def sqlite_file(self) -> Path | None:
        url = self.database_url
        if url.startswith("sqlite:///./"):
            return BACKEND_ROOT / url.replace("sqlite:///./", "", 1)
        if url.startswith("sqlite:///"):
            return Path(url.replace("sqlite:///", "", 1))
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
