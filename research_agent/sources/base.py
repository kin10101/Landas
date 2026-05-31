from abc import ABC, abstractmethod
from typing import List
from models import SourceData
import httpx


class BaseSource(ABC):
    """Base class for all data sources"""

    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.client = httpx.AsyncClient(timeout=30.0)
        self.data: List[SourceData] = []

    @abstractmethod
    async def fetch(self) -> List[SourceData]:
        """Fetch data from source and return list of SourceData objects"""
        pass

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def __repr__(self):
        return f"<{self.__class__.__name__} enabled={self.enabled}>"
