import json

from app.config import get_settings
from app.connectors.base import BaseConnector
from app.schemas import ConnectorResult


class AppStoreSampleConnector(BaseConnector):
    name = "appstore_sample"

    def fetch(self) -> ConnectorResult:
        try:
            path = get_settings().data_path / "app_candidates.json"
            items = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(items, list):
                raise ValueError("app_candidates.json must be a list")
            return ConnectorResult(status="ok", items=items)
        except Exception as exc:  # noqa: BLE001 — connectors must never crash scans
            return ConnectorResult(
                status="unavailable",
                message=f"source unavailable, showing cached/sample data ({exc})",
                items=[],
            )
