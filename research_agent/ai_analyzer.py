import json
import os
from typing import List
from openai import OpenAI
from models import SourceData, ResearchFinding, EmergingTechnology, EstablishedTechnology, ResearchInsights, ResearchRunSummary


class AIAnalyzer:
    """Analyzes raw source data using OpenAI API to extract meaningful insights"""

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def analyze_sources(
        self, source_data: List[SourceData], target_roles: List[str], research_run_id: str
    ) -> ResearchFinding:
        """Analyze aggregated source data and extract technologies, dependencies, insights"""

        data_summary = self._prepare_data_summary(source_data)

        prompt = f"""
Analyze the following research data collected from multiple sources about technologies, trends, and resources relevant to {', '.join(target_roles)} roles.

DATA COLLECTED:
{data_summary}

Please analyze this data and provide:

1. **Emerging Technologies** - New or rising technologies that are gaining attention (last 3-6 months)
2. **Established Technologies** - Well-known, stable technologies that remain relevant
3. **Deprecated/Declining** - Technologies that are becoming less relevant or obsolete
4. **Skill Dependencies** - Prerequisites and related skills for each technology
5. **Insights** - Key patterns, trends, and gaps you observe

For each technology, extract:
- Name
- Category (Data Pipeline, ML Framework, Vector Database, LLM, etc)
- Relevance score (0-1)
- Why it matters for {target_roles[0]} roles
- Learning resources found (if any)
- Prerequisites
- Trend direction (rising/stable/declining)

Return your analysis as valid JSON following this structure. IMPORTANT: Use ONLY these exact category values:
- "Data Pipeline"
- "ML Framework"
- "Vector Database"
- "LLM"
- "Orchestration"
- "Monitoring"
- "Cloud"
- "Other"

{{
    "emerging_technologies": [
        {{
            "name": "string",
            "category": "Data Pipeline|ML Framework|Vector Database|LLM|Orchestration|Monitoring|Cloud|Other",
            "relevance_score": 0.8,
            "description": "string",
            "why_relevant": "string",
            "source": "HackerNews|GitHub|Dev.to",
            "prerequisites": ["string"],
            "trend_direction": "rising",
            "first_detected": "2026-05-31T00:00:00Z"
        }}
    ],
    "established_technologies": [
        {{
            "name": "string",
            "category": "Data Pipeline|ML Framework|Vector Database|LLM|Orchestration|Monitoring|Cloud|Other",
            "current_adoption": 0.95,
            "trend": "stable",
            "still_relevant": true,
            "recent_updates": "string"
        }}
    ],
    "deprecated_or_declining": [
        {{
            "name": "string",
            "reason": "string",
            "replacement": "string"
        }}
    ],
    "skill_dependencies": {{
        "Technology Name": ["Prerequisite 1", "Prerequisite 2"]
    }},
    "insights": {{
        "top_communities": ["string"],
        "most_discussed_technologies": ["string"],
        "emerging_trends": ["string"],
        "skill_gaps_identified": ["string"],
        "technology_intersections": ["string"]
    }}
}}

Be comprehensive but concise. Focus on practical, actionable insights.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            # Extract text from response
            analysis_text = response.choices[0].message.content

            analysis_json = self._extract_json(analysis_text)

            return self._build_research_finding(
                analysis_json, source_data, target_roles, research_run_id
            )

        except Exception as e:
            print(f"[!] AI Analysis Error: {str(e)}")
            return ResearchFinding(
                research_run_id=research_run_id,
                target_roles=target_roles,
                summary=ResearchRunSummary(
                    total_sources_queried=len(set(d.source for d in source_data)),
                    technologies_found=0,
                    new_technologies=0,
                    deprecated_technologies=0,
                    execution_time_seconds=0,
                    errors=[f"AI Analysis failed: {str(e)}"],
                ),
            )

    def _prepare_data_summary(self, source_data: List[SourceData]) -> str:
        """Prepare a text summary of collected data"""
        grouped = {}
        for data in source_data:
            if data.source not in grouped:
                grouped[data.source] = []
            grouped[data.source].append(data)

        summary = []
        for source, items in grouped.items():
            summary.append(f"\n## {source} ({len(items)} items)")
            for item in items[:10]:  # Limit to 10 per source for context
                summary.append(f"- **{item.title}**: {item.description[:100]}")
                summary.append(f"  URL: {item.url}")

        return "\n".join(summary)

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from Claude response"""
        try:
            # Try to find JSON block
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                json_str = text.strip()

            # Try to parse
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse JSON from response: {str(e)}")
            print(f"Debug - First 200 chars of response: {text[:200]}")
            return {
                "emerging_technologies": [],
                "established_technologies": [],
                "deprecated_or_declining": [],
                "skill_dependencies": {},
                "insights": {
                    "top_communities": [],
                    "most_discussed_technologies": [],
                    "emerging_trends": [],
                    "skill_gaps_identified": [],
                    "technology_intersections": [],
                },
            }
        except Exception as e:
            print(f"Warning: Unexpected error extracting JSON: {str(e)}")
            return {
                "emerging_technologies": [],
                "established_technologies": [],
                "deprecated_or_declining": [],
                "skill_dependencies": {},
                "insights": {
                    "top_communities": [],
                    "most_discussed_technologies": [],
                    "emerging_trends": [],
                    "skill_gaps_identified": [],
                    "technology_intersections": [],
                },
            }

    def _build_research_finding(
        self,
        analysis: dict,
        source_data: List[SourceData],
        target_roles: List[str],
        research_run_id: str,
    ) -> ResearchFinding:
        """Convert analysis to ResearchFinding object"""
        from datetime import datetime

        emerging = []
        for tech in analysis.get("emerging_technologies", []):
            try:
                # Add defaults for missing fields
                if "source" not in tech:
                    tech["source"] = "Multiple"
                if "first_detected" not in tech:
                    tech["first_detected"] = datetime.utcnow()

                emerging.append(EmergingTechnology(**tech))
            except Exception as e:
                print(f"Warning: Could not parse emerging tech: {str(e)}")

        established = []
        for tech in analysis.get("established_technologies", []):
            try:
                established.append(EstablishedTechnology(**tech))
            except Exception as e:
                print(f"Warning: Could not parse established tech: {str(e)}")

        insights = ResearchInsights(**analysis.get("insights", {}))

        summary = ResearchRunSummary(
            total_sources_queried=len(set(d.source for d in source_data)),
            technologies_found=len(emerging) + len(established),
            new_technologies=len(emerging),
            deprecated_technologies=len(analysis.get("deprecated_or_declining", [])),
            execution_time_seconds=0,
            sources_used=list(set(d.source for d in source_data)),
        )

        return ResearchFinding(
            research_run_id=research_run_id,
            target_roles=target_roles,
            emerging_technologies=emerging,
            established_technologies=established,
            deprecated_or_declining=analysis.get("deprecated_or_declining", []),
            skill_dependencies=analysis.get("skill_dependencies", {}),
            insights=insights,
            summary=summary,
        )
