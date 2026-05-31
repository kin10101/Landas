import httpx
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from .base import BaseSource
from models import SourceData

if TYPE_CHECKING:
    from progress import ProgressCallback


class StackOverflowSource(BaseSource):
    """Fetch trending tags and questions from Stack Overflow API"""

    BASE_URL = "https://api.stackexchange.com/2.3"

    TAGS = [
        "machine-learning",
        "python",
        "pandas",
        "tensorflow",
        "pytorch",
        "apache-spark",
        "sql",
        "data-science",
        "deep-learning",
        "nlp",
        "langchain",
        "llm",
    ]

    def __init__(self, enabled: bool = True, limit: int = 20, progress_callback: Optional["ProgressCallback"] = None):
        super().__init__("StackOverflow", enabled, progress_callback)
        self.limit = limit

    async def fetch(self) -> List[SourceData]:
        """Fetch trending questions from Stack Overflow"""
        if not self.enabled:
            return []

        from progress import EventType
        total_tags = len(self.TAGS)
        await self.emit_progress(EventType.SOURCE_STARTED, total_items=total_tags, detail="Fetching questions")

        try:
            questions_per_tag = max(1, self.limit // len(self.TAGS))

            for i, tag in enumerate(self.TAGS):
                await self.emit_progress(
                    EventType.SOURCE_ITERATION,
                    current=i + 1,
                    total=total_tags,
                    detail=f"Fetching [{tag}]"
                )

                try:
                    params = {
                        "order": "desc",
                        "sort": "activity",
                        "tagged": tag,
                        "site": "stackoverflow",
                        "pagesize": questions_per_tag,
                        "filter": "withbody",
                    }

                    response = await self.client.get(f"{self.BASE_URL}/questions", params=params)
                    response.raise_for_status()
                    data = response.json()

                    for item in data.get("items", []):
                        created = datetime.fromtimestamp(item.get("creation_date", 0))

                        source_data = SourceData(
                            title=item.get("title", ""),
                            description=item.get("body", "")[:500] if item.get("body") else "",
                            url=item.get("link", ""),
                            source="StackOverflow",
                            timestamp=created,
                            raw_data={
                                "tag": tag,
                                "score": item.get("score", 0),
                                "view_count": item.get("view_count", 0),
                                "answer_count": item.get("answer_count", 0),
                                "is_answered": item.get("is_answered", False),
                                "tags": item.get("tags", []),
                            },
                        )
                        self.data.append(source_data)

                except Exception as e:
                    print(f"  Warning: Could not fetch SO tag {tag}: {str(e)}")
                    continue

            await self.emit_progress(EventType.SOURCE_COMPLETED, items_collected=len(self.data))
            print(f"[+] StackOverflow: Fetched {len(self.data)} questions")
            return self.data

        except Exception as e:
            await self.emit_progress(EventType.SOURCE_FAILED, error=str(e))
            print(f"[!] StackOverflow Error: {str(e)}")
            return []
