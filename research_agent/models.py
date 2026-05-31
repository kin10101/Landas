from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TrendDirection(str, Enum):
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"


class TechCategory(str, Enum):
    DATA_PIPELINE = "Data Pipeline"
    ML_FRAMEWORK = "ML Framework"
    VECTOR_DB = "Vector Database"
    LLM = "LLM"
    ORCHESTRATION = "Orchestration"
    MONITORING = "Monitoring"
    CLOUD = "Cloud"
    OTHER = "Other"


class LearningResource(BaseModel):
    title: str
    url: str
    resource_type: str = Field(..., alias="type")  # tutorial, docs, article, course, video
    source: Optional[str] = None
    relevance_score: Optional[float] = None


class TechnologyDependency(BaseModel):
    name: str
    relationship_type: str = "prerequisite"  # prerequisite, similar, alternative


class EmergingTechnology(BaseModel):
    name: str
    category: TechCategory
    relevance_score: float = Field(ge=0, le=1)
    source: str  # HackerNews, GitHub, etc
    description: str
    why_relevant: str
    learning_resources: List[LearningResource] = []
    prerequisites: List[str] = []
    dependencies: List[TechnologyDependency] = []
    first_detected: datetime
    trend_direction: TrendDirection
    urls: List[str] = []
    mention_count: int = 1
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class EstablishedTechnology(BaseModel):
    name: str
    category: TechCategory
    current_adoption: float = Field(ge=0, le=1)
    trend: TrendDirection
    still_relevant: bool = True
    recent_updates: Optional[str] = None
    learning_resources: List[LearningResource] = []
    last_major_update: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class DeprecatedTechnology(BaseModel):
    name: str
    reason: str
    replacement: Optional[str] = None
    deprecation_date: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ResearchInsights(BaseModel):
    top_communities: List[str] = []
    most_discussed_technologies: List[str] = []
    emerging_trends: List[str] = []
    skill_gaps_identified: List[str] = []
    technology_intersections: List[str] = []  # e.g., "LLMs + Vector DBs"


class ResearchRunSummary(BaseModel):
    total_sources_queried: int
    technologies_found: int
    new_technologies: int
    deprecated_technologies: int
    execution_time_seconds: float
    sources_used: List[str] = []
    errors: List[str] = []


class SkillDependencies(BaseModel):
    skill_name: str
    prerequisites: List[str] = []
    related_skills: List[str] = []
    builds_to: List[str] = []


class ResearchFinding(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    research_run_id: str
    target_roles: List[str]
    emerging_technologies: List[EmergingTechnology] = []
    established_technologies: List[EstablishedTechnology] = []
    deprecated_or_declining: List[DeprecatedTechnology] = []
    skill_dependencies: dict[str, List[str]] = {}
    insights: ResearchInsights = Field(default_factory=ResearchInsights)
    summary: ResearchRunSummary = Field(default_factory=ResearchRunSummary)


class SourceData(BaseModel):
    """Generic data structure for raw data from sources"""
    title: str
    description: Optional[str] = None
    url: str
    source: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_data: dict = {}
