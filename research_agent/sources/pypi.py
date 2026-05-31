import httpx
from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from .base import BaseSource
from models import SourceData

if TYPE_CHECKING:
    from progress import ProgressCallback


class PyPISource(BaseSource):
    """Fetch popular and trending Python packages from PyPI"""

    BASE_URL = "https://pypi.org/pypi"

    PACKAGES = [
        "torch", "tensorflow", "jax", "scikit-learn", "xgboost", "lightgbm",
        "transformers", "langchain", "llama-index", "openai", "anthropic",
        "sentence-transformers", "spacy", "nltk",
        "pandas", "polars", "dask", "vaex", "modin",
        "chromadb", "pinecone-client", "weaviate-client", "qdrant-client",
        "apache-airflow", "prefect", "dagster", "dbt-core",
        "matplotlib", "plotly", "streamlit", "gradio",
    ]

    def __init__(self, enabled: bool = True, limit: int = 25, progress_callback: Optional["ProgressCallback"] = None):
        super().__init__("PyPI", enabled, progress_callback)
        self.limit = limit

    async def fetch(self) -> List[SourceData]:
        """Fetch package info from PyPI"""
        if not self.enabled:
            return []

        from progress import EventType
        packages_to_fetch = self.PACKAGES[:self.limit]
        total_packages = len(packages_to_fetch)
        await self.emit_progress(EventType.SOURCE_STARTED, total_items=total_packages, detail="Fetching packages")

        try:
            for i, package_name in enumerate(packages_to_fetch):
                if (i + 1) % 5 == 0 or i == 0:
                    await self.emit_progress(
                        EventType.SOURCE_ITERATION,
                        current=i + 1,
                        total=total_packages,
                        detail=f"Fetching {package_name}"
                    )

                try:
                    response = await self.client.get(f"{self.BASE_URL}/{package_name}/json")

                    if response.status_code == 404:
                        continue

                    response.raise_for_status()
                    data = response.json()

                    info = data.get("info", {})

                    releases = data.get("releases", {})
                    latest_version = info.get("version", "")
                    release_date = datetime.now()

                    if latest_version and latest_version in releases:
                        release_info = releases[latest_version]
                        if release_info and len(release_info) > 0:
                            upload_time = release_info[0].get("upload_time")
                            if upload_time:
                                try:
                                    release_date = datetime.fromisoformat(upload_time)
                                except:
                                    pass

                    source_data = SourceData(
                        title=f"{info.get('name', package_name)} v{latest_version}",
                        description=info.get("summary", "")[:500],
                        url=info.get("project_url", f"https://pypi.org/project/{package_name}/"),
                        source="PyPI",
                        timestamp=release_date,
                        raw_data={
                            "package_name": package_name,
                            "version": latest_version,
                            "author": info.get("author", ""),
                            "license": info.get("license", ""),
                            "home_page": info.get("home_page", ""),
                            "keywords": info.get("keywords", ""),
                            "requires_python": info.get("requires_python", ""),
                        },
                    )
                    self.data.append(source_data)

                except Exception as e:
                    continue

            await self.emit_progress(EventType.SOURCE_COMPLETED, items_collected=len(self.data))
            print(f"[+] PyPI: Fetched {len(self.data)} packages")
            return self.data

        except Exception as e:
            await self.emit_progress(EventType.SOURCE_FAILED, error=str(e))
            print(f"[!] PyPI Error: {str(e)}")
            return []
