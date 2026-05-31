"""
Landas API Backend

Endpoints:
- GET /api/trees - List all skill trees
- GET /api/tree/{role_id} - Get skill tree
- POST /api/tree/generate - Generate new skill tree
- POST /api/research/run - Run research agent
- GET /api/research/status - Get research status
- PUT /api/progress/{node_id} - Update node progress
- GET /api/discoveries - Get discovered technologies
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add research_agent to path
research_agent_path = Path(__file__).parent.parent / 'research_agent'
sys.path.insert(0, str(research_agent_path))

from dotenv import load_dotenv
load_dotenv()

from database import Database, NodeStatus
from skill_tree_generator import SkillTreeGenerator
from research_runner import ResearchRunner


# Global state
db: Database = None
research_status = {
    "running": False,
    "last_run": None,
    "last_result": None,
    "error": None
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db
    db_path = Path(__file__).parent.parent / 'research_agent' / 'landas.db'
    db = Database(str(db_path))
    yield
    db.close()


app = FastAPI(
    title="Landas API",
    description="AI Career Roadmap API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class ProgressUpdate(BaseModel):
    status: str  # active, in_progress, completed, removed
    notes: Optional[str] = None


class TreeGenerateRequest(BaseModel):
    role: str


# --- Tree Endpoints ---

@app.get("/api/trees")
def list_trees():
    """List all skill trees"""
    roots = db.get_root_nodes()
    return {
        "trees": [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "created_at": r["created_at"]
            }
            for r in roots
        ]
    }


@app.get("/api/tree/{role_id}")
def get_tree(role_id: int):
    """Get full skill tree with progress"""
    tree = db.get_full_tree(role_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Tree not found")
    return tree


@app.post("/api/tree/generate")
async def generate_tree(request: TreeGenerateRequest, background_tasks: BackgroundTasks):
    """Generate a new skill tree for a role"""
    # Check if already exists
    existing = db.get_root_nodes()
    for root in existing:
        if root["name"].lower() == request.role.lower():
            return {"message": "Tree already exists", "id": root["id"]}

    generator = SkillTreeGenerator(db)
    root_id = generator.generate_tree(request.role)

    if root_id:
        return {"message": "Tree generated", "id": root_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to generate tree")


# --- Progress Endpoints ---

@app.put("/api/progress/{node_id}")
def update_progress(node_id: int, update: ProgressUpdate):
    """Update progress on a skill node"""
    node = db.get_skill_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    status_map = {
        "active": NodeStatus.ACTIVE,
        "in_progress": NodeStatus.IN_PROGRESS,
        "completed": NodeStatus.COMPLETED,
        "removed": NodeStatus.REMOVED,
    }

    if update.status not in status_map:
        raise HTTPException(status_code=400, detail="Invalid status")

    db.set_user_progress(node_id, status_map[update.status], update.notes)

    return {"message": "Progress updated", "node_id": node_id, "status": update.status}


@app.get("/api/progress/stats/{role_id}")
def get_progress_stats(role_id: int):
    """Get progress statistics for a tree"""
    def count_nodes(node, stats):
        if node.get("level") != "role":
            stats["total"] += 1
            progress = node.get("progress")
            if progress:
                status = progress.get("status", "active")
                if status == "completed":
                    stats["completed"] += 1
                elif status == "in_progress":
                    stats["in_progress"] += 1
                elif status == "removed":
                    stats["removed"] += 1
        for child in node.get("children", []):
            count_nodes(child, stats)
        return stats

    tree = db.get_full_tree(role_id)
    if not tree:
        raise HTTPException(status_code=404, detail="Tree not found")

    stats = count_nodes(tree, {"total": 0, "completed": 0, "in_progress": 0, "removed": 0})
    stats["percent_complete"] = round((stats["completed"] / stats["total"]) * 100, 1) if stats["total"] > 0 else 0

    return stats


# --- Research Endpoints ---

@app.post("/api/research/run")
async def run_research(background_tasks: BackgroundTasks):
    """Run the research agent"""
    global research_status

    if research_status["running"]:
        return {"message": "Research already running", "status": research_status}

    research_status["running"] = True
    research_status["error"] = None

    background_tasks.add_task(execute_research)

    return {"message": "Research started", "status": research_status}


async def execute_research():
    """Execute research in background"""
    global research_status

    try:
        config_path = Path(__file__).parent.parent / 'research_agent' / 'config.yaml'
        runner = ResearchRunner(str(config_path))
        json_output, table_output, finding = await runner.run(output_format="json")

        research_status["last_run"] = datetime.now().isoformat()
        research_status["last_result"] = {
            "sources_queried": finding.summary.total_sources_queried if finding else 0,
            "technologies_found": finding.summary.technologies_found if finding else 0,
            "new_technologies": finding.summary.new_technologies if finding else 0,
            "execution_time": finding.summary.execution_time_seconds if finding else 0,
        }

        await runner.cleanup()

    except Exception as e:
        research_status["error"] = str(e)

    finally:
        research_status["running"] = False


@app.get("/api/research/status")
def get_research_status():
    """Get research agent status"""
    return research_status


@app.get("/api/discoveries")
def get_discoveries(limit: int = 50, emerging_only: bool = False):
    """Get discovered technologies"""
    discoveries = db.get_all_discoveries(emerging_only=emerging_only)
    return {
        "count": len(discoveries),
        "discoveries": discoveries[:limit]
    }


# --- Health ---

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
