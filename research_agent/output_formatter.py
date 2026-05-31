import json
from typing import List
from datetime import datetime
from models import ResearchFinding


class OutputFormatter:
    """Formats research findings for terminal display"""

    @staticmethod
    def format_json(finding: ResearchFinding) -> str:
        """Format as JSON"""
        data = {
            "timestamp": finding.timestamp.isoformat(),
            "research_run_id": finding.research_run_id,
            "target_roles": finding.target_roles,
            "findings": {
                "emerging_technologies": [
                    {
                        "name": t.name,
                        "category": t.category.value,
                        "relevance_score": t.relevance_score,
                        "source": t.source,
                        "description": t.description,
                        "why_relevant": t.why_relevant,
                        "prerequisites": t.prerequisites,
                        "trend_direction": t.trend_direction.value,
                        "mention_count": t.mention_count,
                    }
                    for t in finding.emerging_technologies
                ],
                "established_technologies": [
                    {
                        "name": t.name,
                        "category": t.category.value,
                        "current_adoption": t.current_adoption,
                        "trend": t.trend.value,
                        "still_relevant": t.still_relevant,
                        "recent_updates": t.recent_updates,
                    }
                    for t in finding.established_technologies
                ],
                "deprecated_or_declining": [
                    {
                        "name": t.name,
                        "reason": t.reason,
                        "replacement": t.replacement,
                    }
                    for t in finding.deprecated_or_declining
                ],
                "skill_dependencies": finding.skill_dependencies,
                "insights": {
                    "top_communities": finding.insights.top_communities,
                    "most_discussed_technologies": finding.insights.most_discussed_technologies,
                    "emerging_trends": finding.insights.emerging_trends,
                    "skill_gaps_identified": finding.insights.skill_gaps_identified,
                    "technology_intersections": finding.insights.technology_intersections,
                },
            },
            "summary": {
                "total_sources_queried": finding.summary.total_sources_queried,
                "technologies_found": finding.summary.technologies_found,
                "new_technologies": finding.summary.new_technologies,
                "deprecated_technologies": finding.summary.deprecated_technologies,
                "execution_time_seconds": finding.summary.execution_time_seconds,
                "sources_used": finding.summary.sources_used,
                "errors": finding.summary.errors,
            },
        }
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def format_table(finding: ResearchFinding) -> str:
        """Format as human-readable table"""
        output = []
        output.append("\n" + "=" * 80)
        output.append("[RESEARCH FINDINGS] - " + finding.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"))
        output.append("=" * 80)

        output.append(f"\nTarget Roles: {', '.join(finding.target_roles)}")
        output.append(f"Research Run ID: {finding.research_run_id}")

        # Emerging Technologies
        if finding.emerging_technologies:
            output.append("\n" + "-" * 80)
            output.append("[NEW] EMERGING TECHNOLOGIES ({} found)".format(
                len(finding.emerging_technologies)
            ))
            output.append("-" * 80)

            for i, tech in enumerate(finding.emerging_technologies, 1):
                output.append(f"\n{i}. {tech.name} [{tech.category.value}]")
                output.append(f"   Relevance: {tech.relevance_score:.1%} | Trend: {tech.trend_direction.value}")
                output.append(f"   Description: {tech.description}")
                output.append(f"   Why Relevant: {tech.why_relevant}")
                if tech.prerequisites:
                    output.append(f"   Prerequisites: {', '.join(tech.prerequisites)}")
                if tech.urls:
                    output.append(f"   Sources: {', '.join(tech.urls[:2])}")

        # Established Technologies
        if finding.established_technologies:
            output.append("\n" + "-" * 80)
            output.append("[STABLE] ESTABLISHED TECHNOLOGIES ({} found)".format(
                len(finding.established_technologies)
            ))
            output.append("-" * 80)

            for i, tech in enumerate(finding.established_technologies, 1):
                output.append(f"\n{i}. {tech.name} [{tech.category.value}]")
                output.append(f"   Adoption: {tech.current_adoption:.1%} | Trend: {tech.trend.value}")
                output.append(f"   Still Relevant: {'Yes' if tech.still_relevant else 'No'}")
                if tech.recent_updates:
                    output.append(f"   Recent Updates: {tech.recent_updates}")

        # Deprecated
        if finding.deprecated_or_declining:
            output.append("\n" + "-" * 80)
            output.append("[DEPRECATED] TECHNOLOGIES ({} found)".format(
                len(finding.deprecated_or_declining)
            ))
            output.append("-" * 80)

            for i, tech in enumerate(finding.deprecated_or_declining, 1):
                output.append(f"\n{i}. {tech.name}")
                output.append(f"   Reason: {tech.reason}")
                if tech.replacement:
                    output.append(f"   Replacement: {tech.replacement}")

        # Insights
        if finding.insights.most_discussed_technologies:
            output.append("\n" + "-" * 80)
            output.append("[INSIGHTS] KEY FINDINGS")
            output.append("-" * 80)

            output.append(
                f"\nMost Discussed: {', '.join(finding.insights.most_discussed_technologies[:5])}"
            )
            if finding.insights.skill_gaps_identified:
                output.append(
                    f"Skill Gaps: {', '.join(finding.insights.skill_gaps_identified[:5])}"
                )
            if finding.insights.technology_intersections:
                output.append(
                    f"Key Intersections: {', '.join(finding.insights.technology_intersections[:3])}"
                )

        # Summary
        output.append("\n" + "-" * 80)
        output.append("[SUMMARY] STATISTICS")
        output.append("-" * 80)
        output.append(f"Sources Queried: {finding.summary.total_sources_queried}")
        output.append(f"Sources Used: {', '.join(finding.summary.sources_used)}")
        output.append(f"Total Technologies Found: {finding.summary.technologies_found}")
        output.append(f"New Technologies: {finding.summary.new_technologies}")
        output.append(f"Deprecated: {finding.summary.deprecated_technologies}")
        if finding.summary.errors:
            output.append(f"Errors: {len(finding.summary.errors)}")
            for error in finding.summary.errors:
                output.append(f"  - {error}")

        output.append("\n" + "=" * 80)

        return "\n".join(output)

    @staticmethod
    def save_to_file(finding: ResearchFinding, filepath: str, format: str = "json"):
        """Save findings to file"""
        if format == "json":
            content = OutputFormatter.format_json(finding)
        else:
            content = OutputFormatter.format_table(finding)

        with open(filepath, "w") as f:
            f.write(content)

        print(f"[+] Results saved to {filepath}")
