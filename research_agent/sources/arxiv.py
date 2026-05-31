import httpx
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
import xml.etree.ElementTree as ET
from .base import BaseSource
from models import SourceData

if TYPE_CHECKING:
    from progress import ProgressCallback


class ArXivSource(BaseSource):
    """Fetch research papers from ArXiv API"""

    BASE_URL = "https://export.arxiv.org/api/query"

    CATEGORIES = [
        "cs.AI",
        "cs.LG",
        "cs.CL",
        "cs.CV",
        "stat.ML",
        "cs.DB",
    ]

    def __init__(self, enabled: bool = True, limit: int = 15, progress_callback: Optional["ProgressCallback"] = None):
        super().__init__("ArXiv", enabled, progress_callback)
        self.limit = limit

    async def fetch(self) -> List[SourceData]:
        """Fetch recent papers from ArXiv"""
        if not self.enabled:
            return []

        from progress import EventType
        await self.emit_progress(EventType.SOURCE_STARTED, total_items=1, detail="Fetching papers")

        try:
            cat_query = " OR ".join([f"cat:{cat}" for cat in self.CATEGORIES])
            params = {
                "search_query": cat_query,
                "start": 0,
                "max_results": self.limit,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }

            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            root = ET.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            entries = root.findall("atom:entry", ns)
            total = len(entries)

            for i, entry in enumerate(entries):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                link = entry.find("atom:id", ns)
                published = entry.find("atom:published", ns)

                categories = [
                    cat.get("term")
                    for cat in entry.findall("atom:category", ns)
                ]

                authors = [
                    author.find("atom:name", ns).text
                    for author in entry.findall("atom:author", ns)
                    if author.find("atom:name", ns) is not None
                ]

                pub_date = datetime.now()
                if published is not None and published.text:
                    try:
                        pub_date = datetime.fromisoformat(published.text.replace("Z", "+00:00"))
                    except:
                        pass

                source_data = SourceData(
                    title=title.text.strip().replace("\n", " ") if title is not None else "",
                    description=summary.text.strip()[:500].replace("\n", " ") if summary is not None else "",
                    url=link.text if link is not None else "",
                    source="ArXiv",
                    timestamp=pub_date,
                    raw_data={
                        "categories": categories,
                        "authors": authors[:3],
                    },
                )
                self.data.append(source_data)

                if (i + 1) % 5 == 0 or i == total - 1:
                    await self.emit_progress(
                        EventType.SOURCE_ITERATION,
                        current=i + 1,
                        total=total,
                        detail="Processing papers"
                    )

            await self.emit_progress(EventType.SOURCE_COMPLETED, items_collected=len(self.data))
            print(f"[+] ArXiv: Fetched {len(self.data)} papers")
            return self.data

        except Exception as e:
            await self.emit_progress(EventType.SOURCE_FAILED, error=str(e))
            print(f"[!] ArXiv Error: {str(e)}")
            return []
