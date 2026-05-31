import httpx
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from bs4 import BeautifulSoup
from .base import BaseSource
from models import SourceData

if TYPE_CHECKING:
    from progress import ProgressCallback


class GitHubTrendingSource(BaseSource):
    """Fetch trending repositories from GitHub"""

    BASE_URL = "https://github.com/trending"

    def __init__(self, enabled: bool = True, limit: int = 25, progress_callback: Optional["ProgressCallback"] = None):
        super().__init__("GitHub", enabled, progress_callback)
        self.limit = limit
        self.languages = ["python", "javascript", "go", "rust"]

    async def fetch(self) -> List[SourceData]:
        """Fetch trending repos from GitHub"""
        if not self.enabled:
            return []

        from progress import EventType
        total_langs = len(self.languages)
        await self.emit_progress(EventType.SOURCE_STARTED, total_items=total_langs, detail="Fetching trending repos")

        try:
            for i, lang in enumerate(self.languages):
                await self.emit_progress(
                    EventType.SOURCE_ITERATION,
                    current=i + 1,
                    total=total_langs,
                    detail=f"Fetching {lang} repos"
                )

                url = f"{self.BASE_URL}?language={lang}&since=weekly"
                response = await self.client.get(url)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                repos = soup.find_all("article", class_="Box-row")

                for repo in repos[: self.limit // len(self.languages)]:
                    try:
                        h2 = repo.find("h2")
                        if not h2:
                            continue

                        repo_link = h2.find("a")
                        repo_name = repo_link.get("href", "").strip("/")
                        repo_url = f"https://github.com{repo_link.get('href', '')}"

                        description_elem = repo.find("p", class_="col-9")
                        description = (
                            description_elem.get_text(strip=True)
                            if description_elem
                            else ""
                        )

                        stars_elem = repo.find("svg", class_="octicon-star")
                        stars = "N/A"
                        if stars_elem:
                            stars_text = stars_elem.parent.get_text(strip=True)
                            stars = stars_text.split()[0]

                        source_data = SourceData(
                            title=repo_name,
                            description=description,
                            url=repo_url,
                            source="GitHub",
                            timestamp=datetime.utcnow(),
                            raw_data={"language": lang, "stars": stars},
                        )
                        self.data.append(source_data)
                    except Exception as e:
                        print(f"  Warning: Could not parse repo: {str(e)}")
                        continue

            await self.emit_progress(EventType.SOURCE_COMPLETED, items_collected=len(self.data))
            print(f"[+] GitHub: Fetched {len(self.data)} trending repos")
            return self.data

        except Exception as e:
            await self.emit_progress(EventType.SOURCE_FAILED, error=str(e))
            print(f"[!] GitHub Error: {str(e)}")
            return []
