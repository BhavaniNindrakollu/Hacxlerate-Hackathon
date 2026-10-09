from app.config import get_settings
from app.connectors.appstore_sample import AppStoreSampleConnector
from app.connectors.base import BaseConnector
from app.connectors.live_connector import LiveAppStoreConnector, LiveSocialConnector
from app.connectors.social_sample import SocialSampleConnector


def get_social_connector() -> BaseConnector:
    if get_settings().connector_mode.strip().lower() == "live":
        return LiveSocialConnector()
    return SocialSampleConnector()


def get_app_connector() -> BaseConnector:
    if get_settings().connector_mode.strip().lower() == "live":
        return LiveAppStoreConnector()
    return AppStoreSampleConnector()
