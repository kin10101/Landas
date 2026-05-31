import httpx
from typing import List
from datetime import datetime
from .base import BaseSource
from models import SourceData


class PyPISource(BaseSource):
    """Fetch popular and trending Python packages from PyPI"""

    BASE_URL = "https://pypi.org/pypi"

    # Key packages to monitor for Data/AI roles
    PACKAGES = [
        # ML/AI Frameworks
        "torch", "tensorflow", "jax", "scikit-learn", "xgboost", "lightgbm",
        # LLM/NLP
        "transformers", "langchain", "llama-index", "openai", "anthropic",
        "sentence-transformers", "spacy", "nltk",
        # Data Processing
        "pandas", "polars", "dask", "vaex", "modin",
        # Vector DBs
        "chromadb", "pinecone-client", "weaviate-client", "qdrant-client",
        # Data Engineering
        "apache-airflow", "prefect", "dagster", "dbt-core",
        # Visualization
        "matplotlib", "plotly", "streamlit", "gradio",
    ]

    def __init__(self, enabled: bool = True, limit: int = 25):
        super().__init__("PyPI", enabled)
        self.limit = limit

    async def fetch(self) -> List[SourceData]:
        """Fetch package info from PyPI"""
        if not self.enabled:
            return []

        try:
            packages_to_fetch = self.PACKAGES[:self.limit]

            for package_name in packages_to_fetch:
                try:
                    response = await self.client.get(f"{self.BASE_URL}/{package_name}/json")

                    if response.status_code == 404:
                        continue

                    response.raise_for_status()
                    data = response.json()

                    info = data.get("info", {})

                    # Get release date
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
                    # Skip packages that fail
                    continue

            print(f"[+] PyPI: Fetched {len(self.data)} packages")
            return self.data

        except Exception as e:
            print(f"[!] PyPI Error: {str(e)}")
            return []
