# Landas - Technical Specifications

## System Overview

Landas is an AI-powered career development platform that creates personalized skill roadmaps for tech professionals (Data Engineers, AI Engineers, etc.) with real-time industry trend monitoring.

---

## 1. Research Agent Module

### Purpose
Autonomous research system that discovers emerging and established technologies, tools, frameworks, and best practices relevant to Data & AI roles.

### Data Sources (Enable/Disable Configuration)

**High-Priority Sources:**
- [ ] HackerNews (news.ycombinator.com/api) - Tech trends, startup announcements
- [ ] GitHub Trending (github.com/trending) - Popular repos by language
- [ ] Reddit (r/MachineLearning, r/datascience, r/learnprogramming) - Community discussions
- [ ] Twitter/X API - Industry experts, announcements
- [ ] dev.to API - Technical articles and tutorials
- [ ] Medium API - In-depth technical posts
- [ ] ArXiv API - Research papers in AI/ML
- [ ] Product Hunt API - New tools and products
- [ ] Stack Overflow Tags - Popular questions/trends
- [ ] Kaggle API - Competitions, datasets, trending notebooks
- [ ] PyPI Stats - Python package popularity trends
- [ ] NPM Trends - JavaScript ecosystem trends
- [ ] Docker Hub - Container image popularity
- [ ] Indie Hackers - Startup and tool discussions
- [ ] Substack (select AI/data newsletters) - Industry insights
- [ ] Coursera/Udemy trending - Learning content demand
- [ ] Job postings APIs (Indeed, LinkedIn) - Skill demand analysis

**Optional Sources:**
- [ ] Conference talks (YouTube - PyCon, DataTalks, etc.)
- [ ] GitHub Releases (automation for key repos)
- [ ] Company tech blogs (OpenAI, Anthropic, Google, Meta, etc.)
- [ ] Podcast transcripts (partial, curated)

### Research Agent Workflow

```
[Scheduled Trigger Weekly OR Manual Trigger]
       ↓
[Initialize Data Sources - Load Config]
       ↓
[Parallel Data Collection from Enabled Sources]
       ↓
[Data Aggregation & Deduplication]
       ↓
[AI Analysis (Claude API): Extract Skills, Resources, Dependencies]
       ↓
[Store Results in PostgreSQL]
       ↓
[Output to Terminal/Console for User Review]
```

### Research Agent Configuration

**Config File: `research_agent/config.yaml`**

```yaml
research_agent:
  enabled_sources:
    hackernews: true
    github_trending: true
    reddit: true
    twitter: false  # Optional
    devto: true
    medium: true
    arxiv: true
    producthunt: true
    stackoverflow: true
    kaggle: true
    pypi_stats: true
    npm_trends: true
    docker_hub: true
    indie_hackers: true
    substack: false  # Optional
    coursera: false  # Optional
    
  target_roles:
    - "Data Engineer"
    - "ML Engineer"
    - "AI Engineer"
    - "Analytics Engineer"
    
  keywords:
    data_tech:
      - dbt
      - Apache Spark
      - pandas
      - SQL
      - Snowflake
      - BigQuery
      - Delta Lake
    ai_tech:
      - LLMs
      - RAG
      - Vector Databases
      - Transformers
      - PyTorch
      - TensorFlow
      
  update_frequency: "weekly"  # or "manual"
  schedule_time: "07:00"  # UTC
  
  api_keys:
    twitter: "${TWITTER_API_KEY}"
    kaggle: "${KAGGLE_API_KEY}"
    # Other optional APIs
```

### Research Agent Output Format

**Terminal Output (JSON structure):**
```json
{
  "timestamp": "2026-05-30T07:00:00Z",
  "research_run_id": "uuid",
  "target_roles": ["Data Engineer", "AI Engineer"],
  "findings": {
    "emerging_technologies": [
      {
        "name": "Tool/Framework Name",
        "category": "Data Pipeline|ML Framework|Vector DB|etc",
        "relevance_score": 0.85,
        "source": "HackerNews|GitHub|etc",
        "description": "Brief description",
        "why_relevant": "Why it matters for Data/AI roles",
        "learning_resources": [
          {"title": "Resource", "url": "link", "type": "tutorial|docs|article"}
        ],
        "prerequisites": ["Python", "SQL"],
        "first_detected": "2026-05-20",
        "trend_direction": "rising|stable|declining"
      }
    ],
    "established_technologies": [
      {
        "name": "Technology",
        "current_adoption": 0.95,
        "trend": "stable|declining",
        "still_relevant": true,
        "recent_updates": "What's new",
        "learning_resources": []
      }
    ],
    "deprecated_or_declining": [
      {
        "name": "Technology",
        "reason": "Why it's becoming obsolete",
        "replacement": "Suggested alternative"
      }
    ],
    "skill_dependencies": {
      "RAG Systems": ["LLMs", "Vector Databases", "Python", "API Design"],
      "dbt": ["SQL", "Git", "Data Warehousing"]
    },
    "insights": {
      "top_communities": ["r/MachineLearning", "r/datascience"],
      "most_discussed_technologies": ["LLMs", "Vector DBs"],
      "skill_gaps": ["LLM Fine-tuning", "Production ML Ops"]
    }
  },
  "summary": {
    "total_sources_queried": 15,
    "technologies_found": 47,
    "new_technologies": 12,
    "deprecated_technologies": 3,
    "execution_time_seconds": 245
  }
}
```

### Research Agent Capabilities

1. **Multi-Source Data Collection** - Parallel fetching from configured sources
2. **Deduplication** - Remove duplicate technology mentions across sources
3. **AI Analysis** - Use Claude API to extract meaning, dependencies, and relevance
4. **Ranking** - Score technologies by emerging/established and relevance to target roles
5. **Change Detection** - Compare with previous runs to identify new/deprecated tech
6. **Learning Resource Curation** - Automatically find tutorials, docs, courses
7. **Terminal Output** - Display results for manual review before saving to DB

---

## 2. Technology Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI (for eventual API layer)
- **Task Scheduling:** APScheduler (for weekly automated runs)
- **AI/LLM:** OpenAI API (gpt-4o-mini for cost efficiency)
- **HTTP Client:** httpx (async)
- **Data Processing:** pandas, pydantic

### Research Agent Module
- **Location:** `research_agent/`
- **Entry Point:** `research_agent/main.py` (terminal-runnable script)
- **Config:** `research_agent/config.yaml`
- **Sources:** Individual modules in `research_agent/sources/`

### Frontend
- **Framework:** React 18+
- **State Management:** TBD (Redux/Zustand/Context)
- **Styling:** TBD (Tailwind/Styled Components)

### Database
- **PostgreSQL** with:
  - Skills table
  - Technologies table
  - Research findings table
  - User roadmaps table
  - Learning resources table
  - Skill dependencies table

### External APIs
- Anthropic Claude API (analysis)
- GitHub API (trending)
- Reddit API (PRAW)
- HackerNews API (Algolia)
- Twitter API v2 (optional)
- ArXiv API
- PyPI JSON API
- Kaggle API

---

## 3. Directory Structure

```
landas/
├── README.md
├── SPECIFICATIONS.md
├── requirements.txt
├── .env.example
│
├── research_agent/
│   ├── main.py                 # Entry point - runnable script
│   ├── config.yaml             # Configuration file (enable/disable sources)
│   ├── research_runner.py       # Main research orchestration logic
│   ├── ai_analyzer.py           # Claude API integration for analysis
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py             # Base source class
│   │   ├── hackernews.py
│   │   ├── github_trending.py
│   │   ├── reddit.py
│   │   ├── devto.py
│   │   ├── medium.py
│   │   ├── arxiv.py
│   │   ├── producthunt.py
│   │   ├── stackoverflow.py
│   │   ├── kaggle_source.py
│   │   ├── pypi_stats.py
│   │   ├── twitter_source.py
│   │   └── [other sources...]
│   ├── models.py               # Pydantic models for research data
│   ├── utils.py
│   └── output_formatter.py     # Format output for terminal/JSON
│
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── database.py
│   ├── models.py               # SQLAlchemy models
│   ├── routes/
│   │   ├── roadmaps.py
│   │   ├── skills.py
│   │   └── research.py
│   └── services/
│       ├── skill_service.py
│       └── research_service.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── App.jsx
│   └── package.json
│
└── tests/
    ├── research_agent_tests.py
    └── [other tests...]
```

---

## 4. Implementation Phases

### Phase 1: Research Agent Module (Terminal)
- [ ] Implement base source fetcher class
- [ ] Integrate 5-7 key data sources (HackerNews, GitHub, Reddit, dev.to, Medium, ArXiv, Kaggle)
- [ ] Claude API integration for analysis
- [ ] Configuration system (enable/disable sources)
- [ ] Terminal output with JSON formatting
- [ ] Manual execution capability
- [ ] Database schema for storing findings

### Phase 2: Automation & API
- [ ] APScheduler integration for weekly runs
- [ ] FastAPI endpoints to trigger/view research results
- [ ] Database persistence
- [ ] Add remaining data sources

### Phase 3: Skill Graph & Frontend
- [ ] Skill graph data model
- [ ] React UI for viewing roadmap
- [ ] Skill progression system

### Phase 4: Personalization & Intelligence Digest
- [ ] User profiles and preferences
- [ ] Weekly digest generation
- [ ] Recommendation engine

---

## 5. Key Decisions

1. **Terminal-First Approach:** Research agent runs as standalone script for easy testing/adjustment before API integration
2. **Modular Sources:** Each data source is independent, can be toggled on/off
3. **AI Analysis:** Claude API extracts relationships, dependencies, and relevance (not just data aggregation)
4. **Weekly Default:** Automated runs weekly to keep data fresh without overwhelming sources
5. **PostgreSQL:** Single relational DB for both structured data and metadata about findings

---

## Next Steps

1. Create research agent module structure
2. Implement base source fetcher class
3. Build 3-4 key sources (HackerNews, GitHub, Reddit, dev.to)
4. Test Claude API integration
5. Build terminal output formatter
6. Get user feedback on output quality before moving to automation
