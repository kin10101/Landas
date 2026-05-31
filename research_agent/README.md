# Landas Research Agent - Phase 1

Terminal-based research agent that discovers emerging and established technologies from multiple sources using OpenAI.

## Quick Start

### 1. Install Dependencies

```bash
cd research_agent
python -m pip install -r ../requirements.txt
```

### 2. Set Up Environment

```bash
cp ../env.example ../.env
# Edit .env and add your OPENAI_API_KEY
```

Required environment variables:
- `OPENAI_API_KEY` - Your OpenAI API key (get from https://platform.openai.com/account/api-keys)
- `OPENAI_MODEL` - Model choice (default: `gpt-4o-mini`, options: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`)

Optional (for Reddit):
- `REDDIT_CLIENT_ID`
- `REDDIT_CLIENT_SECRET`
- `REDDIT_USER_AGENT`

### 3. Run the Research Agent

```bash
# From research_agent directory
python main.py

# Specify output format
python main.py --format table  # Human-readable output
python main.py --format json   # Structured JSON output
python main.py --format both   # Both formats (default)

# Use custom config
python main.py --config config.yaml --format table
```

## Architecture

### Data Sources (Enable/Disable in config.yaml)

Currently enabled by default:
- **HackerNews** - Tech news and stories via Algolia API
- **GitHub Trending** - Popular repositories
- **Dev.to** - Technical articles and tutorials

Currently disabled (can be enabled):
- **Reddit** - Community discussions (requires API credentials)
- **Medium, ArXiv, ProductHunt, etc** - Additional sources

### Workflow

```
Config (YAML) → Data Collection (Parallel) → AI Analysis (OpenAI) → Output (JSON/Table)
```

1. **Data Collection**: Fetch from enabled sources in parallel
2. **AI Analysis**: OpenAI analyzes collected data and extracts:
   - Emerging technologies with relevance scores
   - Established and stable technologies
   - Deprecated or declining tech
   - Skill dependencies and prerequisites
   - Key insights and trends
3. **Output**: Save as JSON and/or human-readable table

### Configuration

Edit `config.yaml` to:
- Enable/disable data sources
- Set target roles (Data Engineer, AI Engineer, ML Engineer, Analytics Engineer)
- Define keywords to track
- Adjust API limits per source

## 🔧 API Key Setup

### Get Your OpenAI API Key

1. Visit https://platform.openai.com/account/api-keys
2. Create a new API key
3. Copy it to your `.env` file:
   ```
   OPENAI_API_KEY=sk-proj-your-key-here
   ```

### Model Selection

Edit `.env` to choose your model:

```bash
# Fastest & Cheapest (Recommended for development)
OPENAI_MODEL=gpt-4o-mini

# Best Quality
OPENAI_MODEL=gpt-4o

# Good Balance
OPENAI_MODEL=gpt-4-turbo

# Budget Option
OPENAI_MODEL=gpt-3.5-turbo
```

## Sample Output

When you run the agent, you get:

**Terminal Output** (Table Format):
```
[RESEARCH FINDINGS] - 2026-05-30 13:08:24 UTC

Target Roles: Data Engineer, AI Engineer, ML Engineer, Analytics Engineer

[NEW] EMERGING TECHNOLOGIES (12 found)
...
[STABLE] ESTABLISHED TECHNOLOGIES (35 found)
...
[DEPRECATED] TECHNOLOGIES (3 found)
...
[INSIGHTS] KEY FINDINGS
...
[SUMMARY] STATISTICS
```

**Saved Files**:
- `research_findings_20260530_130824.json` - Structured data for processing
- `research_findings_20260530_130824.txt` - Human-readable report

## Next Steps

- Connect to database for persistence
- Schedule weekly automated runs
- Build REST API endpoints
- Create web UI for visualization
- Add more data sources (Reddit with auth, Twitter, ArXiv, etc)
- Set up proper logging and monitoring

## Project Structure

```
research_agent/
├── main.py                 # Entry point
├── research_runner.py      # Orchestration logic
├── ai_analyzer.py          # OpenAI API integration
├── output_formatter.py     # JSON/Table formatting
├── models.py               # Pydantic data models
├── utils.py                # Helper functions
├── config.yaml             # Configuration
└── sources/
    ├── base.py             # Base class for sources
    ├── hackernews.py
    ├── github_trending.py
    ├── devto.py
    └── reddit.py
```

## Troubleshooting

**"Config file not found"**
- Run from the research_agent directory, or provide full path with `--config`

**"No data collected"**
- Check internet connection
- Source APIs may be rate-limited or down
- Check config.yaml to ensure sources are enabled

**"Error code: 401 - invalid_api_key"**
- Verify OPENAI_API_KEY is set correctly in .env
- Check your API key at https://platform.openai.com/account/api-keys
- Make sure the key hasn't expired

**"Windows Unicode errors"**
- Resolved; emoji characters replaced with ASCII symbols

## Cost Estimation

Using `gpt-4o-mini` (recommended):
- ~500 tokens per research run
- ~$0.0001 per run with gpt-4o-mini
- ~$0.005 per week with weekly runs

View pricing: https://openai.com/pricing
