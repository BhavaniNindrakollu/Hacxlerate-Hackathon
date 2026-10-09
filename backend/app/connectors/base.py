from abc import ABC, abstractmethod

from app.schemas import ConnectorResult


class BaseConnector(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> ConnectorResult:
        """Never raise: return status ok or unavailable."""
