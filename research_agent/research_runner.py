import asyncio
import time
import uuid
from typing import List, Tuple
from datetime import datetime
import yaml

from sources.hackernews import HackerNewsSource
from sources.github_trending import GitHubTrendingSource
from sources.devto import DevToSource
from sources.medium import MediumSource
from sources.arxiv import ArXivSource
from sources.stackoverflow import StackOverflowSource
from sources.pypi import PyPISource
from models import SourceData
from ai_analyzer import AIAnalyzer
from output_formatter import OutputFormatter
from database import Database


class ResearchRunner:
    """Orchestrates the research process with database integration"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.sources = self._initialize_sources()
        self.analyzer = AIAnalyzer()

        # Initialize database
        db_path = self.config["research_agent"].get("database", {}).get("path", "landas.db")
        self.db = Database(db_path)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    def _initialize_sources(self) -> dict:
        """Initialize data sources based on config"""
        enabled_sources = self.config["research_agent"]["enabled_sources"]
        limits = self.config["research_agent"]["api_limits"]

        sources = {}

        if enabled_sources.get("hackernews"):
            sources["hackernews"] = HackerNewsSource(
                enabled=True, limit=limits.get("hackernews_stories", 30)
            )

        if enabled_sources.get("github_trending"):
            sources["github"] = GitHubTrendingSource(
                enabled=True, limit=limits.get("github_trending_repos", 25)
            )

        if enabled_sources.get("devto"):
            sources["devto"] = DevToSource(
                enabled=True, limit=limits.get("devto_articles", 20)
            )

        if enabled_sources.get("medium"):
            sources["medium"] = MediumSource(
                enabled=True, limit=limits.get("medium_articles", 20)
            )

        if enabled_sources.get("arxiv"):
            sources["arxiv"] = ArXivSource(
                enabled=True, limit=limits.get("arxiv_papers", 15)
            )

        if enabled_sources.get("stackoverflow"):
            sources["stackoverflow"] = StackOverflowSource(
                enabled=True, limit=limits.get("stackoverflow_questions", 20)
            )

        if enabled_sources.get("pypi"):
            sources["pypi"] = PyPISource(
                enabled=True, limit=limits.get("pypi_packages", 25)
            )

        return sources

    async def run(self, output_format: str = "both") -> Tuple:
        """Execute research pipeline with database tracking

        Args:
            output_format: 'json', 'table', or 'both'

        Returns:
            Tuple of (json_output, table_output, research_finding)
        """
        print("\n" + "=" * 80)
        print("[*] STARTING RESEARCH AGENT")
        print("=" * 80)

        start_time = time.time()
        research_run_id = str(uuid.uuid4())

        print(f"\nResearch Run ID: {research_run_id}")
        print(f"Targets: {', '.join(self.config['research_agent']['target_roles'])}")
        print(f"Active Sources: {len(self.sources)}")

        # Check previous discoveries
        previous_discoveries = self.db.get_all_discoveries()
        if previous_discoveries:
            print(f"[*] Found {len(previous_discoveries)} previously discovered technologies")

        # Collect data from all sources
        print("\n[*] COLLECTING DATA FROM SOURCES...")
        all_data = await self._collect_from_sources()

        if not all_data:
            print("[!] No data collected from any source")
            return None, None, None

        print(f"\n[+] Total items collected: {len(all_data)}")

        # Analyze with OpenAI (include context about previous discoveries)
        print("\n[*] ANALYZING WITH OPENAI...")
        research_finding = self.analyzer.analyze_sources(
            all_data,
            self.config["research_agent"]["target_roles"],
            research_run_id,
            previous_discoveries=previous_discoveries,
        )

        # Update execution time
        exec_time = time.time() - start_time
        research_finding.summary.execution_time_seconds = exec_time

        # Save to database
        self._save_to_database(research_run_id, research_finding, all_data)

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

        print(f"\n[+] Research completed in {exec_time:.2f}s")

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
                print(f"[!] Source error: {str(result)}")
            elif isinstance(result, list):
                all_data.extend(result)

        return all_data

    def _save_to_database(self, run_id: str, finding, all_data: List[SourceData]):
        """Save research findings to database"""
        try:
            # Save research run
            sources_used = list(set(d.source for d in all_data))
            db_run_id = self.db.save_research_run(
                run_id=run_id,
                target_roles=finding.target_roles,
                sources=sources_used,
                items_collected=len(all_data),
                techs_found=finding.summary.technologies_found,
                exec_time=finding.summary.execution_time_seconds,
            )

            # Save discovered technologies
            for tech in finding.emerging_technologies:
                self.db.save_tech_discovery(
                    name=tech.name,
                    category=tech.category.value if hasattr(tech.category, 'value') else str(tech.category),
                    description=tech.description,
                    relevance=tech.relevance_score,
                    trend=tech.trend_direction.value if hasattr(tech.trend_direction, 'value') else str(tech.trend_direction),
                    source=tech.source,
                    is_emerging=True,
                    research_run_id=db_run_id,
                )

            for tech in finding.established_technologies:
                self.db.save_tech_discovery(
                    name=tech.name,
                    category=tech.category.value if hasattr(tech.category, 'value') else str(tech.category),
                    description=tech.recent_updates or "",
                    relevance=tech.current_adoption,
                    trend=tech.trend.value if hasattr(tech.trend, 'value') else str(tech.trend),
                    source="Multiple",
                    is_emerging=False,
                    research_run_id=db_run_id,
                )

            print(f"[+] Saved research run to database (ID: {db_run_id})")

        except Exception as e:
            print(f"[!] Database save error: {str(e)}")

    def get_previous_discoveries(self) -> List[dict]:
        """Get all previously discovered technologies"""
        return self.db.get_all_discoveries()

    def get_research_history(self, limit: int = 10) -> List[dict]:
        """Get recent research run history"""
        return self.db.get_recent_runs(limit)

    async def cleanup(self):
        """Close connections"""
        for source in self.sources.values():
            await source.close()
        self.db.close()


async def main():
    """Main entry point"""
    runner = ResearchRunner("config.yaml")

    try:
        json_output, table_output, finding = await runner.run(output_format="both")

        # Save to files
        if finding:
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
        print(f"[!] Error: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
