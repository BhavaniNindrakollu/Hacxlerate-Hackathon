import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

HANDLE_RE = re.compile(r"^@?[A-Za-z0-9._]{2,50}$")
PACKAGE_RE = re.compile(r"^[A-Za-z0-9._]{2,200}$")
PLATFORMS = {"twitter", "x", "instagram", "facebook", "youtube", "linkedin", "telegram"}
STORES = {"play", "appstore", "playstore", "google_play", "apple"}


class HealthResponse(BaseModel):
    status: str = "ok"
    app: str
    environment: str


class SourceStatus(BaseModel):
    name: str
    status: Literal["ok", "unavailable"]
    message: str | None = None
    using_cached: bool = False


class ConnectorResult(BaseModel):
    status: Literal["ok", "unavailable"]
    message: str | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)


class OfficialSocialIn(BaseModel):
    platform: str
    handle: str

    @field_validator("platform")
    @classmethod
    def platform_ok(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned == "x":
            cleaned = "twitter"
        if cleaned not in PLATFORMS:
            raise ValueError(f"Unsupported platform. Use one of: {', '.join(sorted(PLATFORMS))}")
        return cleaned

    @field_validator("handle")
    @classmethod
    def handle_ok(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned.startswith("@"):
            cleaned = cleaned[1:]
        if not HANDLE_RE.match(cleaned):
            raise ValueError("Handle must be 2–50 letters, numbers, dots or underscores")
        return cleaned


class OfficialAppIn(BaseModel):
    store: str
    package_id: str
    developer_name: str

    @field_validator("store")
    @classmethod
    def store_ok(cls, value: str) -> str:
        cleaned = value.strip().lower().replace(" ", "_")
        aliases = {"google_play": "play", "playstore": "play", "play_store": "play", "ios": "appstore"}
        cleaned = aliases.get(cleaned, cleaned)
        if cleaned not in {"play", "appstore"}:
            raise ValueError("Store must be play or appstore")
        return cleaned

    @field_validator("package_id")
    @classmethod
    def package_ok(cls, value: str) -> str:
        cleaned = value.strip()
        if not PACKAGE_RE.match(cleaned):
            raise ValueError("Package id must be letters, numbers, dots or underscores")
        return cleaned

    @field_validator("developer_name")
    @classmethod
    def developer_ok(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Developer name is required")
        return cleaned


class BrandIn(BaseModel):
    company_name: str = Field(min_length=2, max_length=200)
    keywords: list[str] = Field(default_factory=list)
    social_accounts: list[OfficialSocialIn] = Field(default_factory=list)
    official_apps: list[OfficialAppIn] = Field(default_factory=list)

    @field_validator("company_name")
    @classmethod
    def name_ok(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Company name is required")
        return cleaned

    @field_validator("keywords")
    @classmethod
    def keywords_ok(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]


class OfficialSocialOut(OfficialSocialIn):
    id: int


class OfficialAppOut(OfficialAppIn):
    id: int


class BrandOut(BaseModel):
    id: int
    company_name: str
    logo_url: str | None
    keywords: list[str]
    social_accounts: list[OfficialSocialOut]
    official_apps: list[OfficialAppOut]
    is_demo: bool = False


class SignupIn(BaseModel):
    email: str
    password: str
    full_name: str = Field(default="", max_length=120)


class LoginIn(BaseModel):
    email: str
    password: str


class RoleUpdateIn(BaseModel):
    role: str
    is_active: bool | None = None


class DeleteHistoryIn(BaseModel):
    confirmation: str
    create_backup: bool = True


class SourceToggleIn(BaseModel):
    simulate_social_unavailable: bool | None = None
    simulate_apps_unavailable: bool | None = None


class SourcesOut(BaseModel):
    social: SourceStatus
    apps: SourceStatus
    simulate_social_unavailable: bool
    simulate_apps_unavailable: bool
    connector_mode: str
