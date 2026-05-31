import httpx
from typing import List
from datetime import datetime
from .base import BaseSource
from models import SourceData


class DevToSource(BaseSource):
    """Fetch articles from dev.to API"""

    BASE_URL = "https://dev.to/api/articles"

    def __init__(self, enabled: bool = True, limit: int = 20):
        super().__init__("Dev.to", enabled)
        self.limit = limit
        self.tags = ["machinelearning", "dataengineering", "python", "ai", "llm"]

    async def fetch(self) -> List[SourceData]:
        """Fetch articles from dev.to"""
        if not self.enabled:
            return []

        try:
            for tag in self.tags:
                params = {
                    "tag": tag,
                    "per_page": self.limit // len(self.tags),
                    "top": 7,  # Last 7 days
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

            print(f"[+] Dev.to: Fetched {len(self.data)} articles")
            return self.data

        except Exception as e:
            print(f"[!] Dev.to Error: {str(e)}")
            return []
