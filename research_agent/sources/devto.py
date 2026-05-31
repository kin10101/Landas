import httpx
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from .base import BaseSource
from models import SourceData

if TYPE_CHECKING:
    from progress import ProgressCallback


class DevToSource(BaseSource):
    """Fetch articles from dev.to API"""

    BASE_URL = "https://dev.to/api/articles"

    def __init__(self, enabled: bool = True, limit: int = 20, progress_callback: Optional["ProgressCallback"] = None):
        super().__init__("Dev.to", enabled, progress_callback)
        self.limit = limit
        self.tags = ["machinelearning", "dataengineering", "python", "ai", "llm"]

    async def fetch(self) -> List[SourceData]:
        """Fetch articles from dev.to"""
        if not self.enabled:
            return []

        from progress import EventType
        total_tags = len(self.tags)
        await self.emit_progress(EventType.SOURCE_STARTED, total_items=total_tags, detail="Fetching articles")

        try:
            for i, tag in enumerate(self.tags):
                await self.emit_progress(
                    EventType.SOURCE_ITERATION,
                    current=i + 1,
                    total=total_tags,
                    detail=f"Fetching #{tag}"
                )

                params = {
                    "tag": tag,
                    "per_page": self.limit // len(self.tags),
                    "top": 7,
                }

                response = await self.client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                articles = response.json()

                for article in articles:
                    source_data = SourceData(
                        title=article.get("title", ""),
                        description=article.get("description", "")[:500],
                        url=article.get("url", ""),
                        source="Dev.to",
                        timestamp=datetime.fromisoformat(
                            article.get("published_at", "").replace("Z", "+00:00")
                        ),
                        raw_data={
                            "tag": tag,
                            "author": article.get("user", {}).get("name", ""),
                            "reading_time": article.get("reading_time_minutes", 0),
                            "reactions": article.get("reactions_count", 0),
                        },
                    )
                    self.data.append(source_data)

            await self.emit_progress(EventType.SOURCE_COMPLETED, items_collected=len(self.data))
            print(f"[+] Dev.to: Fetched {len(self.data)} articles")
            return self.data

        except Exception as e:
            await self.emit_progress(EventType.SOURCE_FAILED, error=str(e))
            print(f"[!] Dev.to Error: {str(e)}")
            return []
