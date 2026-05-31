import asyncio
import time
import uuid
from typing import List
from datetime import datetime
import yaml

from sources.hackernews import HackerNewsSource
from sources.github_trending import GitHubTrendingSource
from sources.devto import DevToSource
from models import SourceData
from ai_analyzer import AIAnalyzer
from output_formatter import OutputFormatter


class ResearchRunner:
    """Orchestrates the research process"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.sources = self._initialize_sources()
        self.analyzer = AIAnalyzer()

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def _initialize_sources(self) -> dict:
        """Initialize data sources based on config"""
        enabled_sources = self.config["research_agent"]["enabled_sources"]

        sources = {}

        if enabled_sources.get("hackernews"):
            sources["hackernews"] = HackerNewsSource(
                enabled=True, limit=self.config["research_agent"]["api_limits"].get("hackernews_stories", 30)
            )

        if enabled_sources.get("github_trending"):
            sources["github"] = GitHubTrendingSource(
                enabled=True,
                limit=self.config["research_agent"]["api_limits"].get("github_trending_repos", 25),
            )

        if enabled_sources.get("devto"):
            sources["devto"] = DevToSource(
                enabled=True, limit=self.config["research_agent"]["api_limits"].get("devto_articles", 20)
            )

        # Reddit requires PRAW with auth - will add when credentials available
        # if enabled_sources.get("reddit"):
        #     sources["reddit"] = RedditSource(...)

        return sources

    async def run(self, output_format: str = "both") -> tuple:
        """Execute research pipeline

        Args:
            output_format: 'json', 'table', or 'both'

        Returns:
            Tuple of (json_output, table_output)
        """
        print("\n" + "=" * 80)
        print("[*] STARTING RESEARCH AGENT")
        print("=" * 80)

        start_time = time.time()
        research_run_id = str(uuid.uuid4())

        print(f"\nResearch Run ID: {research_run_id}")
        print(f"Targets: {', '.join(self.config['research_agent']['target_roles'])}")
        print(f"Active Sources: {len(self.sources)}")

        # Collect data from all sources
        print("\n[*] COLLECTING DATA FROM SOURCES...")
        all_data = await self._collect_from_sources()

        if not all_data:
            print("[!] No data collected from any source")
            return None, None

        print(f"\n[+] Total items collected: {len(all_data)}")

        # Analyze with OpenAI
        print("\n[*] ANALYZING WITH OPENAI...")
        research_finding = self.analyzer.analyze_sources(
            all_data,
            self.config["research_agent"]["target_roles"],
            research_run_id,
        )

        # Update execution time
        research_finding.summary.execution_time_seconds = time.time() - start_time

        # Format output
        print("\n[*] FORMATTING OUTPUT...")

        json_output = None
        table_output = None

        if output_format in ["json", "both"]:
            json_output = OutputFormatter.format_json(research_finding)

        if output_format in ["table", "both"]:
            table_output = OutputFormatter.format_table(research_finding)

        # Display
        if table_output:
            print(table_output)

        print(f"\n[+] Research completed in {research_finding.summary.execution_time_seconds:.2f}s")

        return json_output, table_output, research_finding

    async def _collect_from_sources(self) -> List[SourceData]:
        """Collect data from all enabled sources in parallel"""
        tasks = []

        for source_name, source in self.sources.items():
            if source.enabled:
                tasks.append(source.fetch())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_data = []
        for result in results:
            if isinstance(result, Exception):
                print(f"✗ Source error: {str(result)}")
            elif isinstance(result, list):
                all_data.extend(result)

        return all_data

    async def cleanup(self):
        """Close connections"""
        for source in self.sources.values():
            await source.close()


async def main():
    """Main entry point"""
    runner = ResearchRunner("config.yaml")

    try:
        json_output, table_output, finding = await runner.run(output_format="both")

        # Save to files
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if json_output:
            OutputFormatter.save_to_file(
                finding, f"research_findings_{timestamp}.json", format="json"
            )

        if table_output:
            OutputFormatter.save_to_file(
                finding, f"research_findings_{timestamp}.txt", format="table"
            )

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
