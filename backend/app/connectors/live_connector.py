"""Live API connector interface. Real HTTP sources plug in here later.

Any failure (missing keys, network, rate limit) falls back to sample connectors
so scans never crash.
"""

from app.connectors.appstore_sample import AppStoreSampleConnector
from app.connectors.base import BaseConnector
from app.connectors.social_sample import SocialSampleConnector
from app.schemas import ConnectorResult


class LiveSocialConnector(BaseConnector):
    name = "social_live"

    def fetch(self) -> ConnectorResult:
        try:
            raise NotImplementedError("Live social APIs are not wired yet")
        except Exception as exc:  # noqa: BLE001
            fallback = SocialSampleConnector().fetch()
            return ConnectorResult(
                status="unavailable",
                message=f"source unavailable, showing cached/sample data ({exc})",
                items=fallback.items,
            )


class LiveAppStoreConnector(BaseConnector):
    name = "appstore_live"

    def fetch(self) -> ConnectorResult:
        try:
            raise NotImplementedError("Live app-store APIs are not wired yet")
        except Exception as exc:  # noqa: BLE001
            fallback = AppStoreSampleConnector().fetch()
            return ConnectorResult(
                status="unavailable",
                message=f"source unavailable, showing cached/sample data ({exc})",
                items=fallback.items,
            )
