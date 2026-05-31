from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING
from models import SourceData
import httpx

if TYPE_CHECKING:
    from progress import ProgressCallback


class BaseSource(ABC):
    """Base class for all data sources"""

    def __init__(self, name: str, enabled: bool = True, progress_callback: Optional["ProgressCallback"] = None):
        self.name = name
        self.enabled = enabled
        self.client = httpx.AsyncClient(timeout=30.0)
        self.data: List[SourceData] = []
        self.progress_callback = progress_callback

    @abstractmethod
    async def fetch(self) -> List[SourceData]:
        """Fetch data from source and return list of SourceData objects"""
        pass

    async def emit_progress(self, event_type, **data) -> None:
        """Emit a progress event if callback is set."""
        if self.progress_callback:
            data["source"] = self.name
            await self.progress_callback.emit(event_type, **data)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def __repr__(self):
        return f"<{self.__class__.__name__} enabled={self.enabled}>"
