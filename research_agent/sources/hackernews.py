import httpx
from typing import List
from datetime import datetime
from .base import BaseSource
from models import SourceData


class HackerNewsSource(BaseSource):
    """Fetch trending stories from HackerNews using Algolia API"""

    BASE_URL = "https://hn.algolia.com/api/v1"

    def __init__(self, enabled: bool = True, limit: int = 30):
        super().__init__("HackerNews", enabled)
        self.limit = limit

    async def fetch(self) -> List[SourceData]:
        """Fetch top stories from HackerNews"""
        if not self.enabled:
            return []

        try:
            url = f"{self.BASE_URL}/search?query=AI%20OR%20data%20OR%20machine%20learning&tags=story&hitsPerPage={self.limit}"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            for hit in data.get("hits", [])[:self.limit]:
                source_data = SourceData(
                    title=hit.get("title", ""),
                    description=hit.get("story_text", ""),
                    url=hit.get("url", ""),
                    source="HackerNews",
                    timestamp=datetime.fromtimestamp(hit.get("created_at_i", 0)),
                    raw_data={
                        "points": hit.get("points", 0),
                        "num_comments": hit.get("num_comments", 0),
                        "author": hit.get("author", ""),
                    },
                )
                self.data.append(source_data)

            print(f"[+] HackerNews: Fetched {len(self.data)} stories")
            return self.data

        except Exception as e:
            print(f"[!] HackerNews Error: {str(e)}")
            return []
