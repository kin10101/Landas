import httpx
import feedparser
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from .base import BaseSource
from models import SourceData

if TYPE_CHECKING:
    from progress import ProgressCallback


class MediumSource(BaseSource):
    """Fetch articles from Medium via RSS feeds for tech topics"""

    FEEDS = {
        "ai": "https://medium.com/feed/tag/artificial-intelligence",
        "machine-learning": "https://medium.com/feed/tag/machine-learning",
        "data-science": "https://medium.com/feed/tag/data-science",
        "data-engineering": "https://medium.com/feed/tag/data-engineering",
        "python": "https://medium.com/feed/tag/python",
        "llm": "https://medium.com/feed/tag/llm",
    }

    def __init__(self, enabled: bool = True, limit: int = 20, progress_callback: Optional["ProgressCallback"] = None):
        super().__init__("Medium", enabled, progress_callback)
        self.limit = limit

    async def fetch(self) -> List[SourceData]:
        """Fetch articles from Medium RSS feeds"""
        if not self.enabled:
            return []

        from progress import EventType
        total_feeds = len(self.FEEDS)
        await self.emit_progress(EventType.SOURCE_STARTED, total_items=total_feeds, detail="Fetching RSS feeds")

        try:
            articles_per_feed = max(1, self.limit // len(self.FEEDS))

            for i, (tag, feed_url) in enumerate(self.FEEDS.items()):
                await self.emit_progress(
                    EventType.SOURCE_ITERATION,
                    current=i + 1,
                    total=total_feeds,
                    detail=f"Fetching {tag} feed"
                )

                try:
                    response = await self.client.get(feed_url)
                    response.raise_for_status()

                    feed = feedparser.parse(response.text)

                    for entry in feed.entries[:articles_per_feed]:
                        published = datetime.now()
                        if hasattr(entry, "published_parsed") and entry.published_parsed:
                            published = datetime(*entry.published_parsed[:6])

                        description = entry.get("summary", "")[:500]
                        description = description.replace("<p>", "").replace("</p>", "")

                        source_data = SourceData(
                            title=entry.get("title", ""),
                            description=description,
                            url=entry.get("link", ""),
                            source="Medium",
                            timestamp=published,
                            raw_data={
                                "tag": tag,
                                "author": entry.get("author", ""),
                            },
                        )
                        self.data.append(source_data)

                except Exception as e:
                    print(f"  Warning: Could not fetch Medium feed {tag}: {str(e)}")
                    continue

            await self.emit_progress(EventType.SOURCE_COMPLETED, items_collected=len(self.data))
            print(f"[+] Medium: Fetched {len(self.data)} articles")
            return self.data

        except Exception as e:
            await self.emit_progress(EventType.SOURCE_FAILED, error=str(e))
            print(f"[!] Medium Error: {str(e)}")
            return []
