import asyncio
import time
import uuid
from typing import List, Tuple, Optional
from datetime import datetime
import yaml
from langsmith import traceable

try:
    from .sources.hackernews import HackerNewsSource
    from .sources.github_trending import GitHubTrendingSource
    from .sources.devto import DevToSource
    from .sources.medium import MediumSource
    from .sources.arxiv import ArXivSource
    from .sources.stackoverflow import StackOverflowSource
    from .sources.pypi import PyPISource
    from .models import SourceData
    from .ai_analyzer import AIAnalyzer
    from .output_formatter import OutputFormatter
    from .database import Database
    from .progress import EventType, ProgressCallback, create_progress_callback
except ImportError:
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
    from progress import EventType, ProgressCallback, create_progress_callback


class ResearchRunner:
    """Orchestrates the research process with database integration"""

    def __init__(self, config_path: str = "config.yaml", progress_queue: Optional[asyncio.Queue] = None, db: Optional[Database] = None, debug: bool = False, user_config: dict = None, user_id: Optional[int] = None):
        self.config = self._load_config(config_path)
        self.user_config = user_config
        self._merge_user_config(user_config)
        self.progress_queue = progress_queue
        self.progress_callback = create_progress_callback(progress_queue)
        self.sources = self._initialize_sources()
        self.debug = debug
        self.analyzer = AIAnalyzer(debug=debug)
        self.user_id = user_id

        if db is not None:
            self.db = db
            self._owns_db = False
        else:
            db_path = self.config["research_agent"].get("database", {}).get("path", "landas.db")
            self.db = Database(db_path)
            self._owns_db = True

    def _merge_user_config(self, user_config: dict):
        """Merge user preferences into config"""
        if not user_config:
            return

        ra = self.config["research_agent"]

        # Override target_roles with single user role
        if user_config.get("target_role"):
            ra["target_roles"] = [user_config["target_role"]]

        # Override enabled_sources
        if user_config.get("enabled_sources"):
            for source, enabled in user_config["enabled_sources"].items():
                if source in ra["enabled_sources"]:
                    ra["enabled_sources"][source] = enabled

        # Store relevance threshold
        if user_config.get("relevance_threshold") is not None:
            ra["relevance_threshold"] = user_config["relevance_threshold"]

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
                enabled=True, limit=limits.get("hackernews_stories", 30),
                progress_callback=self.progress_callback
            )

        if enabled_sources.get("github_trending"):
            sources["github"] = GitHubTrendingSource(
                enabled=True, limit=limits.get("github_trending_repos", 25),
                progress_callback=self.progress_callback
            )

        if enabled_sources.get("devto"):
            sources["devto"] = DevToSource(
                enabled=True, limit=limits.get("devto_articles", 20),
                progress_callback=self.progress_callback
            )

        if enabled_sources.get("medium"):
            sources["medium"] = MediumSource(
                enabled=True, limit=limits.get("medium_articles", 20),
                progress_callback=self.progress_callback
            )

        if enabled_sources.get("arxiv"):
            sources["arxiv"] = ArXivSource(
                enabled=True, limit=limits.get("arxiv_papers", 15),
                progress_callback=self.progress_callback
            )

        if enabled_sources.get("stackoverflow"):
            sources["stackoverflow"] = StackOverflowSource(
                enabled=True, limit=limits.get("stackoverflow_questions", 20),
                progress_callback=self.progress_callback
            )

        if enabled_sources.get("pypi"):
            sources["pypi"] = PyPISource(
                enabled=True, limit=limits.get("pypi_packages", 25),
                progress_callback=self.progress_callback
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
        await self._emit_progress(EventType.LOG, message="[*] Starting research agent")

        start_time = time.time()
        research_run_id = str(uuid.uuid4())

        print(f"\nResearch Run ID: {research_run_id}")
        print(f"Targets: {', '.join(self.config['research_agent']['target_roles'])}")
        print(f"Active Sources: {len(self.sources)}")
        await self._emit_progress(
            EventType.LOG,
            message=f"Research Run ID: {research_run_id} | Targets: {', '.join(self.config['research_agent']['target_roles'])} | Active Sources: {len(self.sources)}"
        )

        await self._emit_progress(
            EventType.RESEARCH_STARTED,
            run_id=research_run_id,
            target_roles=self.config["research_agent"]["target_roles"],
            total_sources=len(self.sources),
            source_names=list(self.sources.keys())
        )

        try:
            previous_discoveries = self.db.get_all_discoveries()
            if previous_discoveries:
                print(f"[*] Found {len(previous_discoveries)} previously discovered technologies")
                await self._emit_progress(
                    EventType.LOG,
                    message=f"[*] Found {len(previous_discoveries)} previously discovered technologies"
                )

            print("\n[*] COLLECTING DATA FROM SOURCES...")
            await self._emit_progress(EventType.LOG, message="[*] Collecting data from sources...")
            all_data = await self._collect_from_sources()

            await self._emit_progress(
                EventType.COLLECTION_COMPLETED,
                items_collected=len(all_data),
                sources_completed=len(self.sources)
            )

            if not all_data:
                print("[!] No data collected from any source")
                await self._emit_progress(EventType.RESEARCH_FAILED, error="No data collected")
                return None, None, None

            print(f"\n[+] Total items collected: {len(all_data)}")
            await self._emit_progress(EventType.LOG, message=f"[+] Total items collected: {len(all_data)}")

            print("\n[*] ANALYZING WITH OPENAI...")
            await self._emit_progress(EventType.LOG, message="[*] Analyzing with OpenAI...")
            await self._emit_progress(EventType.ANALYSIS_STARTED, items_to_analyze=len(all_data))

            research_finding = self.analyzer.analyze_sources(
                all_data,
                self.config["research_agent"]["target_roles"],
                research_run_id,
                previous_discoveries=previous_discoveries,
            )

            await self._emit_progress(
                EventType.ANALYSIS_COMPLETED,
                technologies_found=research_finding.summary.technologies_found,
                new_technologies=research_finding.summary.new_technologies,
                deprecated_technologies=research_finding.summary.deprecated_technologies
            )

            for tech in research_finding.emerging_technologies:
                await self._emit_progress(
                    EventType.TECH_DISCOVERED,
                    name=tech.name,
                    category=tech.category.value if hasattr(tech.category, 'value') else str(tech.category),
                    relevance_score=tech.relevance_score,
                    trend=tech.trend_direction.value if hasattr(tech.trend_direction, 'value') else str(tech.trend_direction),
                    is_emerging=True
                )

            exec_time = time.time() - start_time
            research_finding.summary.execution_time_seconds = exec_time

            self._save_to_database(research_run_id, research_finding, all_data)

            print(f"\n[*] ADDING TO SKILL TREE...")
            await self._emit_progress(EventType.LOG, message="[*] Adding findings to skill tree...")
            print(f"[DEBUG] research_finding has {len(research_finding.emerging_technologies)} emerging, {len(research_finding.established_technologies)} established techs")
            added_nodes = await self._add_to_skill_tree(research_finding)
            print(f"[DEBUG] Added {len(added_nodes)} nodes to skill tree")

            print("\n[*] FORMATTING OUTPUT...")
            await self._emit_progress(EventType.LOG, message="[*] Formatting output...")

            json_output = None
            table_output = None

            if output_format in ["json", "both"]:
                json_output = OutputFormatter.format_json(research_finding)

            if output_format in ["table", "both"]:
                table_output = OutputFormatter.format_table(research_finding)

            if table_output:
                print(table_output)

            print(f"\n[+] Research completed in {exec_time:.2f}s")
            await self._emit_progress(EventType.LOG, message=f"[+] Research completed in {exec_time:.2f}s")

            await self._emit_progress(
                EventType.RESEARCH_COMPLETED,
                run_id=research_run_id,
                execution_time=exec_time,
                technologies_found=research_finding.summary.technologies_found,
                new_technologies=research_finding.summary.new_technologies
            )

            return json_output, table_output, research_finding

        except Exception as e:
            await self._emit_progress(EventType.RESEARCH_FAILED, error=str(e))
            raise

    async def _emit_progress(self, event_type: EventType, **data) -> None:
        """Emit a progress event if callback is available."""
        if self.progress_callback:
            await self.progress_callback.emit(event_type, **data)

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

    @traceable(name="add_to_skill_tree")
    async def _add_to_skill_tree(self, finding) -> List[dict]:
        """Add discovered technologies and identify missing skills for the target roles."""
        import json
        import os
        from openai import OpenAI
        from langsmith.wrappers import wrap_openai

        added_nodes = []

        root_nodes = self.db.get_root_nodes(user_id=self.user_id) if self.user_id is not None else self.db.get_root_nodes()
        if not root_nodes:
            print("[!] No skill tree found to add technologies to")
            return added_nodes

        desired_role = None
        if self.user_config and self.user_config.get("target_role"):
            desired_role = self.user_config["target_role"]
        elif finding.target_roles:
            desired_role = finding.target_roles[0]

        root_node = None
        if desired_role:
            desired_lower = desired_role.lower()
            root_node = next((node for node in root_nodes if node["name"].lower() == desired_lower), None)

        if root_node is None:
            root_node = root_nodes[0]

        root_id = root_node["id"]
        tree = self.db.get_full_tree(root_id, user_id=self.user_id) if self.user_id is not None else self.db.get_full_tree(root_id)
        if not tree:
            return added_nodes

        def get_tree_structure(node, depth=0):
            result = {"name": node["name"], "id": node["id"], "level": node.get("level", ""), "children": []}
            for child in node.get("children", []):
                result["children"].append(get_tree_structure(child, depth + 1))
            return result

        def get_existing_names(node, names=None):
            if names is None:
                names = set()
            names.add(node["name"].lower())
            for child in node.get("children", []):
                get_existing_names(child, names)
            return names

        tree_structure = get_tree_structure(tree)
        existing_names = get_existing_names(tree)

        print(f"[DEBUG] Existing skills in tree: {len(existing_names)}")
        await self._emit_progress(EventType.LOG, message=f"[DEBUG] Existing skills in tree: {len(existing_names)}")

        client = wrap_openai(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # Collect all relevant technologies
        all_techs = []

        relevance_threshold = self.config["research_agent"].get("relevance_threshold", 0.5)

        print(f"[DEBUG] Emerging technologies found: {len(finding.emerging_technologies)}")
        await self._emit_progress(EventType.LOG, message=f"[DEBUG] Emerging technologies found: {len(finding.emerging_technologies)}")
        for tech in finding.emerging_technologies:
            print(f"  - {tech.name}: relevance={tech.relevance_score}, in_tree={tech.name.lower() in existing_names}")

        # Add emerging technologies (above relevance threshold)
        for tech in finding.emerging_technologies:
            if tech.relevance_score >= relevance_threshold and tech.name.lower() not in existing_names:
                all_techs.append({
                    "name": tech.name,
                    "category": tech.category.value if hasattr(tech.category, 'value') else str(tech.category),
                    "description": tech.description,
                    "relevance": tech.relevance_score,
                    "trend": "emerging",
                    "source": tech.source
                })

        print(f"[DEBUG] Established technologies found: {len(finding.established_technologies)}")
        await self._emit_progress(EventType.LOG, message=f"[DEBUG] Established technologies found: {len(finding.established_technologies)}")
        for tech in finding.established_technologies:
            print(f"  - {tech.name}: adoption={tech.current_adoption}, in_tree={tech.name.lower() in existing_names}")

        # Add established technologies that might be missing (slightly higher threshold)
        adoption_threshold = relevance_threshold + 0.1
        for tech in finding.established_technologies:
            if tech.current_adoption >= adoption_threshold and tech.name.lower() not in existing_names:
                all_techs.append({
                    "name": tech.name,
                    "category": tech.category.value if hasattr(tech.category, 'value') else str(tech.category),
                    "description": tech.recent_updates or f"Established {tech.category} technology",
                    "relevance": tech.current_adoption,
                    "trend": "stable",
                    "source": "Multiple"
                })

        print(f"[DEBUG] Technologies passing filters: {len(all_techs)}")
        await self._emit_progress(EventType.LOG, message=f"[DEBUG] Technologies passing filters: {len(all_techs)}")
        for tech in all_techs:
            print(f"  - {tech['name']} ({tech['trend']})")

        if not all_techs:
            print("[*] No new technologies to add to skill tree")
            # Still check for missing skills

        print(f"\n[*] Analyzing skill tree for {', '.join(finding.target_roles)}...")
        await self._emit_progress(EventType.LOG, message=f"[*] Analyzing skill tree for {', '.join(finding.target_roles)}...")

        # Ask AI to suggest additions based on research findings
        tech_summary = json.dumps(all_techs[:20], indent=2) if all_techs else "No new specific technologies found"

        prompt = f"""
You are building a comprehensive skill tree for these roles: {', '.join(finding.target_roles)}

Current skill tree structure:
{json.dumps(tree_structure, indent=2)}

Technologies discovered in research:
{tech_summary}

Based on current industry trends and the research findings, suggest up to 8 additions to the skill tree. Consider:
1. Technologies from the research that should be added
2. Important skills/topics that are missing for these roles
3. New categories that would help organize learning

For each suggestion, determine the best placement in the existing tree.

Return ONLY valid JSON array:
[
    {{
        "action": "add",
        "name": "<skill/technology name>",
        "description": "<brief description>",
        "parent_id": <id of parent node to attach to>,
        "level": "category" or "skill" or "subskill",
        "difficulty": 1-5,
        "trend": "emerging" or "stable" or "rising",
        "reason": "<why this should be added>"
    }}
]

Only suggest additions that would genuinely help someone learning these roles. Skip if a similar skill already exists.
Return empty array [] if the tree is already comprehensive.
"""

        # Debug: save skill tree prompt
        if self.debug:
            from pathlib import Path
            debug_dir = Path(__file__).parent / "debug"
            debug_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = debug_dir / f"skilltree_input_{timestamp}.txt"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("SKILL TREE AI INPUT\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"Target roles: {finding.target_roles}\n")
                f.write(f"Existing tree nodes: {len(existing_names)}\n")
                f.write(f"Technologies to consider: {len(all_techs)}\n\n")
                f.write("=" * 80 + "\n")
                f.write("ALL TECHNOLOGIES FOUND\n")
                f.write("=" * 80 + "\n\n")
                f.write(json.dumps(all_techs, indent=2))
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("PROMPT\n")
                f.write("=" * 80 + "\n\n")
                f.write(prompt)
            print(f"[DEBUG] Saved skill tree input to: {debug_file}")

        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4
            )

            text = response.choices[0].message.content
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                json_str = text.strip()

            suggestions = json.loads(json_str)

            # Debug: save AI response
            if self.debug:
                response_file = debug_dir / f"skilltree_output_{timestamp}.txt"
                with open(response_file, "w", encoding="utf-8") as f:
                    f.write("=" * 80 + "\n")
                    f.write("SKILL TREE AI OUTPUT\n")
                    f.write("=" * 80 + "\n\n")
                    f.write("RAW RESPONSE:\n")
                    f.write(text)
                    f.write("\n\n" + "=" * 80 + "\n")
                    f.write("PARSED SUGGESTIONS:\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(json.dumps(suggestions, indent=2))
                print(f"[DEBUG] Saved skill tree output to: {response_file}")

            if not suggestions:
                print("[*] AI determined skill tree is comprehensive")
                await self._emit_progress(EventType.LOG, message="[*] AI determined skill tree is comprehensive")
                return added_nodes

            print(f"[*] Adding {len(suggestions)} skills to the tree...")
            await self._emit_progress(EventType.LOG, message=f"[*] Adding {len(suggestions)} skills to the tree...")

            from database import SkillNodeCreate, NodeLevel, TrendDirection

            level_map = {
                "category": NodeLevel.CATEGORY,
                "skill": NodeLevel.SKILL,
                "subskill": NodeLevel.SUBSKILL
            }

            trend_map = {
                "emerging": TrendDirection.EMERGING,
                "stable": TrendDirection.STABLE,
                "growing": TrendDirection.RISING,
                "rising": TrendDirection.RISING,
                "declining": TrendDirection.DECLINING
            }

            for suggestion in suggestions:
                if suggestion.get("action") != "add":
                    continue

                # Skip if name already exists (case-insensitive)
                if suggestion["name"].lower() in existing_names:
                    print(f"  [~] Skipped (exists): {suggestion['name']}")
                    continue

                try:
                    new_node = SkillNodeCreate(
                        name=suggestion["name"],
                        description=suggestion.get("description", ""),
                        level=level_map.get(suggestion.get("level", "skill"), NodeLevel.SKILL),
                        parent_id=suggestion["parent_id"],
                        difficulty=suggestion.get("difficulty", 3),
                        relevance_score=0.8,
                        trend=trend_map.get(suggestion.get("trend", "stable"), TrendDirection.STABLE),
                        user_id=self.user_id or 1
                    )

                    node_id = self.db.create_skill_node(new_node)
                    existing_names.add(suggestion["name"].lower())

                    # Fetch and add resources for the new node
                    resources_added = await self._fetch_and_add_resources(
                        node_id, suggestion["name"], client, model
                    )

                    added_nodes.append({
                        "id": node_id,
                        "name": suggestion["name"],
                        "parent_id": suggestion["parent_id"],
                        "level": suggestion.get("level", "skill"),
                        "resources_added": resources_added
                    })

                    await self._emit_progress(
                        EventType.TREE_UPDATED,
                        node_id=node_id,
                        node_name=suggestion["name"],
                        parent_id=suggestion["parent_id"],
                        level=suggestion.get("level", "skill"),
                        resources_added=resources_added
                    )

                    print(f"  [+] Added: {suggestion['name']} ({suggestion.get('level', 'skill')}) with {resources_added} resources")
                    await self._emit_progress(
                        EventType.LOG,
                        message=f"[+] Added: {suggestion['name']} ({suggestion.get('level', 'skill')}) with {resources_added} resources"
                    )

                except Exception as e:
                    print(f"  [!] Failed to add {suggestion['name']}: {str(e)}")
                    await self._emit_progress(
                        EventType.LOG,
                        message=f"[!] Failed to add {suggestion['name']}: {str(e)}",
                        level="error"
                    )
                    continue

        except Exception as e:
            print(f"[!] AI analysis error: {str(e)}")
            await self._emit_progress(EventType.LOG, message=f"[!] AI analysis error: {str(e)}", level="error")

        if added_nodes:
            print(f"\n[+] Successfully added {len(added_nodes)} new skills to the tree")
            await self._emit_progress(EventType.LOG, message=f"[+] Successfully added {len(added_nodes)} new skills to the tree")

        return added_nodes

    @traceable(name="fetch_and_add_resources")
    async def _fetch_and_add_resources(self, node_id: int, skill_name: str, client, model: str) -> int:
        """Fetch learning resources for a skill and add them to the database."""
        import json
        from database import ResourceCreate

        prompt = f"""
Find 3-5 high-quality learning resources for "{skill_name}".

Include a mix of:
- Official documentation
- Tutorials or guides
- Video courses or articles

For each resource provide:
- title: Clear, descriptive title
- url: Real, working URL (must be a real resource that exists)
- resource_type: one of [docs, tutorial, video, course, article]
- source: The platform/site name

IMPORTANT: Only include real, existing resources with valid URLs.

Return ONLY valid JSON array:
[
    {{
        "title": "Resource Title",
        "url": "https://...",
        "resource_type": "tutorial",
        "source": "Platform Name"
    }}
]
"""

        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )

            text = response.choices[0].message.content
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                json_str = text.strip()

            resources = json.loads(json_str)

            from url_validator import filter_valid_resources
            valid_resources, invalid = await filter_valid_resources(resources, timeout=5.0)
            if invalid:
                print(f"    [!] Filtered {len(invalid)} invalid resource URLs")
                await self._emit_progress(
                    EventType.LOG,
                    message=f"[!] Filtered {len(invalid)} invalid resource URLs",
                    level="warning"
                )

            added_count = 0

            for res in valid_resources:
                try:
                    resource = ResourceCreate(
                        skill_node_id=node_id,
                        title=res["title"],
                        url=res["url"],
                        resource_type=res.get("resource_type", "article"),
                        source=res.get("source")
                    )
                    self.db.add_resource(resource)
                    added_count += 1
                except Exception as e:
                    print(f"    [!] Failed to add resource: {str(e)}")

            if added_count > 0:
                print(f"    [+] Added {added_count} resources")
                await self._emit_progress(EventType.LOG, message=f"[+] Added {added_count} resources")

            return added_count

        except Exception as e:
            print(f"    [!] Resource fetch error: {str(e)}")
            await self._emit_progress(EventType.LOG, message=f"[!] Resource fetch error: {str(e)}", level="error")
            return 0

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
        if self._owns_db:
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
