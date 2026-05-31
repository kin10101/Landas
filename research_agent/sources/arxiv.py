import httpx
from typing import List
from datetime import datetime
import xml.etree.ElementTree as ET
from .base import BaseSource
from models import SourceData


class ArXivSource(BaseSource):
    """Fetch research papers from ArXiv API"""

    BASE_URL = "https://export.arxiv.org/api/query"

    # ArXiv categories relevant to Data/AI roles
    CATEGORIES = [
        "cs.AI",   # Artificial Intelligence
        "cs.LG",   # Machine Learning
        "cs.CL",   # Computation and Language (NLP)
        "cs.CV",   # Computer Vision
        "stat.ML", # Statistics - Machine Learning
        "cs.DB",   # Databases
    ]

    def __init__(self, enabled: bool = True, limit: int = 15):
        super().__init__("ArXiv", enabled)
        self.limit = limit

    async def fetch(self) -> List[SourceData]:
        """Fetch recent papers from ArXiv"""
        if not self.enabled:
            return []

        try:
            # Build query for multiple categories
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

            # Parse XML response
            root = ET.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                link = entry.find("atom:id", ns)
                published = entry.find("atom:published", ns)

                # Get categories
                categories = [
                    cat.get("term")
                    for cat in entry.findall("atom:category", ns)
                ]

                # Get authors
                authors = [
                    author.find("atom:name", ns).text
                    for author in entry.findall("atom:author", ns)
                    if author.find("atom:name", ns) is not None
                ]

                # Parse date
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
                        "authors": authors[:3],  # Limit to first 3 authors
                    },
                )
                self.data.append(source_data)

            print(f"[+] ArXiv: Fetched {len(self.data)} papers")
            return self.data

        except Exception as e:
            print(f"[!] ArXiv Error: {str(e)}")
            return []
