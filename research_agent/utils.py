"""Utility functions for research agent"""

from typing import List
import re


def extract_technologies(text: str, keywords: List[str]) -> List[str]:
    """Extract mentioned technologies from text"""
    found = set()

    for keyword in keywords:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        if pattern.search(text):
            found.add(keyword)

    return list(found)


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication"""
    return url.rstrip("/").lower()


def deduplicate_sources(source_data_list) -> list:
    """Remove duplicate entries by URL"""
    seen_urls = set()
    unique = []

    for data in source_data_list:
        normalized = normalize_url(data.url)
        if normalized not in seen_urls:
            seen_urls.add(normalized)
            unique.append(data)

    return unique


def calculate_relevance_score(
    mention_count: int,
    days_since_mention: int,
    is_github_trending: bool = False,
    engagement_score: float = 0.5,
) -> float:
    """Calculate relevance score for a technology"""
    # More recent = higher score
    recency_factor = 1.0 - (days_since_mention / 180.0)  # Decay over 6 months
    recency_factor = max(0.1, min(1.0, recency_factor))

    # More mentions = higher score
    mention_factor = min(1.0, mention_count / 10.0)

    # GitHub trending boost
    github_factor = 1.3 if is_github_trending else 1.0

    # Engagement (comments, upvotes)
    engagement_factor = min(1.0, engagement_score)

    score = (recency_factor * 0.3 + mention_factor * 0.3 + engagement_factor * 0.4) * github_factor
    return round(min(1.0, score), 2)
