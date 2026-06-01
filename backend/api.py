"""
Landas API Backend

Endpoints:
- GET /api/trees - List all skill trees
- GET /api/tree/{role_id} - Get skill tree
- POST /api/tree/generate - Generate new skill tree
- POST /api/research/start - Start research with SSE streaming
- GET /api/research/stream/{session_id} - SSE endpoint for progress
- POST /api/research/run - Run research agent (legacy)
- GET /api/research/status - Get research status
- PUT /api/progress/{node_id} - Update node progress
- GET /api/discoveries - Get discovered technologies
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI

from auth import (
    UserCreate, UserLogin, Token, UserResponse,
    get_password_hash, verify_password, create_access_token,
    create_auth_dependency
)

research_agent_path = Path(__file__).parent.parent / 'research_agent'
sys.path.insert(0, str(research_agent_path))

from dotenv import load_dotenv
load_dotenv()

from database import Database, NodeStatus, SkillNodeCreate, NodeLevel, TrendDirection
from skill_tree_generator import SkillTreeGenerator
from research_runner import ResearchRunner


# Initialize database immediately so auth dependency can use it
db_path = Path(__file__).parent.parent / 'research_agent' / 'landas.db'
db = Database(str(db_path))

# Create auth dependency with database
get_current_user = create_auth_dependency(db)

# Global state
research_status = {
    "running": False,
    "last_run": None,
    "last_result": None,
    "error": None
}

# SSE session management
active_research_sessions: dict[str, asyncio.Queue] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database already initialized above
    yield
    db.close()


app = FastAPI(
    title="Landas API",
    description="AI Career Roadmap API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:3000",
]
# Allow all origins in production if CORS_ORIGINS is set to "*"
allow_all = "*" in cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else cors_origins,
    allow_credentials=not allow_all,  # credentials not allowed with wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth Endpoints ---

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    """Register a new user"""
    existing = db.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user_data.password)
    user_id = db.create_user(
        email=user_data.email,
        password_hash=hashed_password,
        name=user_data.name
    )

    user = db.get_user_by_id(user_id)
    access_token = create_access_token(data={"sub": str(user_id)})

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            created_at=user["created_at"]
        )
    )


@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login and get access token"""
    user = db.get_user_by_email(user_data.email)

    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user["id"])})

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            created_at=user["created_at"]
        )
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        created_at=current_user["created_at"]
    )


# --- Models ---

class ProgressUpdate(BaseModel):
    status: str  # active, in_progress, completed, removed
    notes: Optional[str] = None


class TreeGenerateRequest(BaseModel):
    role: str


class TopicResearchRequest(BaseModel):
    topic: str
    tree_id: int


async def run_topic_research(request: TopicResearchRequest, current_user: dict, progress_queue: Optional[asyncio.Queue] = None):
    async def emit_event(event_type: EventType, **data):
        if progress_queue is None:
            return
        event = ProgressEvent(
            type=event_type,
            timestamp=datetime.utcnow(),
            data=data
        )
        await progress_queue.put(event)

    async def emit_log(message: str, level: str = "info"):
        await emit_event(EventType.LOG, message=message, level=level)

    await emit_event(EventType.TOPIC_STARTED, topic=request.topic, tree_id=request.tree_id)
    await emit_log(f"[*] Topic research started: {request.topic}")

    tree = db.get_full_tree(request.tree_id, user_id=current_user["id"])
    if not tree:
        await emit_log("[!] Tree not found for topic research", level="error")
        raise HTTPException(status_code=404, detail="Tree not found")

    def get_tree_structure(node, depth=0):
        result = {"name": node["name"], "id": node["id"], "level": node.get("level", ""), "children": []}
        for child in node.get("children", []):
            result["children"].append(get_tree_structure(child, depth + 1))
        return result

    tree_structure = get_tree_structure(tree)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    await emit_log("[*] Generating topic additions with OpenAI...")

    prompt = f"""
You are helping build a skill tree for career development.

Current tree structure:
{json.dumps(tree_structure, indent=2)}

The user wants to research: "{request.topic}"

Analyze this request:
1. Is the user asking about a single topic, or asking for subtopics/breakdown (e.g., "types of X", "different approaches to Y")?
2. Find the best parent node in the existing tree
3. Generate appropriate nodes with learning resources

If asking for subtopics, create multiple nodes (3-6 subnodes).
If a single topic, create one node.

For EACH node, include 2-3 real learning resources with valid URLs.

Return ONLY valid JSON:
{{
    "relevant": true/false,
    "is_breakdown": true/false,
    "parent_id": <id of parent node>,
    "parent_name": "<parent name>",
    "nodes": [
        {{
            "name": "<skill name>",
            "description": "<brief description>",
            "level": "skill" or "subskill",
            "difficulty": 1-5,
            "resources": [
                {{
                    "title": "<resource title>",
                    "url": "<real URL>",
                    "resource_type": "docs|tutorial|video|article|course",
                    "source": "<platform name>"
                }}
            ]
        }}
    ],
    "reason": "<why this placement>"
}}

IMPORTANT: Only include real, existing resources with valid URLs. Common good sources:
- Official documentation sites
- YouTube tutorials
- Medium/Dev.to articles
- Coursera/Udemy courses
- GitHub repos with good READMEs
"""

    try:
        # Run blocking OpenAI call in thread pool
        def call_openai():
            return client.chat.completions.create(
                model=model,
                max_completion_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
        response = await asyncio.to_thread(call_openai)

        text = response.choices[0].message.content
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            json_str = text.split("```")[1].split("```")[0].strip()
        else:
            json_str = text.strip()

        result = json.loads(json_str)

        if not result.get("relevant"):
            await emit_log("[!] Topic not relevant to this skill tree", level="warning")
            return {
                "success": False,
                "message": result.get("reason", "Topic not relevant to this skill tree")
            }

        if not result.get("nodes"):
            await emit_log("[!] No nodes to add for this topic", level="warning")
            return {
                "success": False,
                "message": "No nodes to add"
            }

        from database import ResourceCreate

        added_nodes = []
        level_map = {"category": "category", "skill": "skill", "subskill": "subskill"}

        await emit_log(f"[*] Adding {len(result['nodes'])} topic nodes to the tree...")

        for node_data in result["nodes"]:
            new_node = SkillNodeCreate(
                name=node_data["name"],
                description=node_data.get("description", ""),
                level=NodeLevel(level_map.get(node_data.get("level", "skill"), "skill")),
                parent_id=result["parent_id"],
                difficulty=node_data.get("difficulty", 3),
                relevance_score=0.8,
                trend=TrendDirection.EMERGING,
                user_id=current_user["id"]
            )

            node_id = db.create_skill_node(new_node)

            resources_added = 0
            resources_list = node_data.get("resources", [])
            if resources_list:
                from url_validator import filter_valid_resources
                valid_resources, invalid_resources = await filter_valid_resources(resources_list, timeout=5.0)
                if invalid_resources:
                    await emit_log(
                        f"[!] Filtered {len(invalid_resources)} invalid resource URLs",
                        level="warning"
                    )
            else:
                valid_resources = []

            for res in valid_resources:
                try:
                    resource = ResourceCreate(
                        skill_node_id=node_id,
                        title=res["title"],
                        url=res["url"],
                        resource_type=res.get("resource_type", "article"),
                        source=res.get("source")
                    )
                    db.add_resource(resource)
                    resources_added += 1
                except Exception:
                    continue

            added_nodes.append({
                "id": node_id,
                "name": node_data["name"],
                "resources_added": resources_added
            })

            await emit_log(f"[+] Added: {node_data['name']} with {resources_added} resources")

        return {
            "success": True,
            "is_breakdown": result.get("is_breakdown", False),
            "nodes_added": len(added_nodes),
            "nodes": added_nodes,
            "placement": {
                "parent_id": result["parent_id"],
                "parent_name": result.get("parent_name", "")
            },
            "reason": result.get("reason", "")
        }

    except Exception as e:
        await emit_log(f"[!] Topic research failed: {str(e)}", level="error")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")


# --- Tree Endpoints ---

@app.get("/api/trees")
def list_trees(current_user: dict = Depends(get_current_user)):
    """List all skill trees for the current user"""
    roots = db.get_root_nodes(user_id=current_user["id"])
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
def get_tree(role_id: int, current_user: dict = Depends(get_current_user)):
    """Get full skill tree with progress"""
    tree = db.get_full_tree(role_id, user_id=current_user["id"])
    if not tree:
        raise HTTPException(status_code=404, detail="Tree not found")
    return tree


@app.post("/api/tree/generate")
async def generate_tree(request: TreeGenerateRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    """Generate a new skill tree for a role"""
    import asyncio

    # Check if already exists for this user
    existing = db.get_root_nodes(user_id=current_user["id"])
    for root in existing:
        if root["name"].lower() == request.role.lower():
            return {"message": "Tree already exists", "id": root["id"]}

    generator = SkillTreeGenerator(db, user_id=current_user["id"])
    # Run blocking OpenAI call in thread pool to not block event loop
    root_id = await asyncio.to_thread(generator.generate_tree, request.role, current_user["id"])

    if root_id:
        return {"message": "Tree generated", "id": root_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to generate tree")


# --- Progress Endpoints ---

@app.put("/api/progress/{node_id}")
def update_progress(node_id: int, update: ProgressUpdate, current_user: dict = Depends(get_current_user)):
    """Update progress on a skill node"""
    node = db.get_skill_node(node_id, user_id=current_user["id"])
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

    db.set_user_progress(node_id, status_map[update.status], update.notes, user_id=current_user["id"])

    return {"message": "Progress updated", "node_id": node_id, "status": update.status}


class PositionUpdate(BaseModel):
    position_x: float
    position_y: float


@app.put("/api/node/{node_id}/position")
def update_node_position(node_id: int, update: PositionUpdate, current_user: dict = Depends(get_current_user)):
    """Update node position for drag and drop"""
    node = db.get_skill_node(node_id, user_id=current_user["id"])
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    db.update_node_position(node_id, update.position_x, update.position_y)
    return {"message": "Position updated", "node_id": node_id}


@app.delete("/api/node/{node_id}")
def delete_node(node_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a skill node and all its children"""
    node = db.get_skill_node(node_id, user_id=current_user["id"])
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    if node.get("level") == "role":
        raise HTTPException(status_code=400, detail="Cannot delete the root node")

    success = db.delete_skill_node(node_id, user_id=current_user["id"])
    if success:
        return {"message": "Node deleted", "node_id": node_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete node")


@app.get("/api/progress/stats/{role_id}")
def get_progress_stats(role_id: int, current_user: dict = Depends(get_current_user)):
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

    tree = db.get_full_tree(role_id, user_id=current_user["id"])
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
        runner = ResearchRunner(str(config_path), db=db)
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


# --- SSE Research Streaming Endpoints ---

@app.post("/api/research/start")
async def start_research_stream(current_user: dict = Depends(get_current_user)):
    """Start research with SSE streaming support"""
    global research_status

    if research_status["running"]:
        return {"message": "Research already running", "status": research_status}

    session_id = str(uuid.uuid4())
    progress_queue = asyncio.Queue()
    active_research_sessions[session_id] = progress_queue

    research_status["running"] = True
    research_status["error"] = None

    asyncio.create_task(execute_research_with_streaming(session_id, progress_queue, current_user["id"]))

    return {"session_id": session_id, "message": "Research started"}


async def execute_research_with_streaming(session_id: str, progress_queue: asyncio.Queue, user_id: int):
    """Execute research with progress streaming"""
    global research_status

    try:
        config_path = Path(__file__).parent.parent / 'research_agent' / 'config.yaml'

        # Load user preferences
        user_prefs = db.get_user_preferences(user_id=user_id)
        user_config = None
        if user_prefs:
            user_config = {
                "target_role": user_prefs.get("target_role", "AI Engineer"),
                "enabled_sources": user_prefs.get("enabled_sources", {}),
                "relevance_threshold": user_prefs.get("relevance_threshold", 0.5)
            }

        # Enable debug mode to save AI inputs/outputs to research_agent/debug/
        runner = ResearchRunner(
            str(config_path),
            progress_queue=progress_queue,
            db=db,
            debug=True,
            user_config=user_config,
            user_id=user_id
        )
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
        from progress import EventType, ProgressEvent
        error_event = ProgressEvent(
            type=EventType.RESEARCH_FAILED,
            timestamp=datetime.utcnow(),
            data={"error": str(e)}
        )
        await progress_queue.put(error_event)

    finally:
        research_status["running"] = False
        await asyncio.sleep(2)
        if session_id in active_research_sessions:
            del active_research_sessions[session_id]


@app.get("/api/research/stream/{session_id}")
async def stream_research_progress(session_id: str):
    """SSE endpoint for streaming research progress"""
    if session_id not in active_research_sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    async def event_generator():
        queue = active_research_sessions[session_id]
        keepalive_interval = 15

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=keepalive_interval)

                event_data = {
                    "type": event.type.value if hasattr(event.type, 'value') else event.type,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data
                }
                yield f"data: {json.dumps(event_data)}\n\n"

                if event.type in ["research_completed", "research_failed", "topic_completed", "topic_failed"]:
                    break

            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/discoveries")
def get_discoveries(limit: int = 50, emerging_only: bool = False):
    """Get discovered technologies"""
    discoveries = db.get_all_discoveries(emerging_only=emerging_only)
    return {
        "count": len(discoveries),
        "discoveries": discoveries[:limit]
    }


# --- Resource Search Endpoints ---

class ResourceSearchRequest(BaseModel):
    query: str
    skill_name: Optional[str] = None
    resource_types: Optional[list[str]] = None


class ResourceAddRequest(BaseModel):
    skill_node_id: int
    title: str
    url: str
    resource_type: str
    source: Optional[str] = None


@app.post("/api/resources/search")
async def search_resources(request: ResourceSearchRequest):
    """Search for learning resources using AI"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    type_filter = ""
    if request.resource_types:
        type_filter = f"\nPrefer these resource types: {', '.join(request.resource_types)}"

    skill_context = ""
    if request.skill_name:
        skill_context = f" for learning {request.skill_name}"

    prompt = f"""
You are a learning resource curator. Find the best resources{skill_context}.

Search query: "{request.query}"
{type_filter}

Return 5-8 high-quality learning resources. Include a mix of:
- Official documentation
- Tutorials and guides
- Video courses
- Articles and blog posts
- Interactive learning platforms

For each resource, provide:
- title: Clear, descriptive title
- url: Real, working URL (must be a real resource that exists)
- resource_type: one of [docs, tutorial, video, course, article, tool]
- source: The platform/site name
- description: 1-2 sentence description
- difficulty: beginner, intermediate, or advanced

IMPORTANT: Only include real, existing resources with valid URLs. Do not make up resources.

Return ONLY valid JSON array:
[
    {{
        "title": "Resource Title",
        "url": "https://...",
        "resource_type": "tutorial",
        "source": "Platform Name",
        "description": "Brief description",
        "difficulty": "beginner"
    }}
]
"""

    try:
        # Run blocking OpenAI call in thread pool
        def call_openai():
            return client.chat.completions.create(
                model=model,
                max_completion_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
        response = await asyncio.to_thread(call_openai)

        text = response.choices[0].message.content
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            json_str = text.split("```")[1].split("```")[0].strip()
        else:
            json_str = text.strip()

        resources = json.loads(json_str)

        from url_validator import filter_valid_resources
        valid_resources, _ = await filter_valid_resources(resources, timeout=3.0)

        return {
            "query": request.query,
            "skill_name": request.skill_name,
            "resources": valid_resources
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resource search failed: {str(e)}")


@app.post("/api/resources/add")
async def add_resource_to_node(request: ResourceAddRequest, current_user: dict = Depends(get_current_user)):
    """Add a resource to a skill node"""
    node = db.get_skill_node(request.skill_node_id, user_id=current_user["id"])
    if not node:
        raise HTTPException(status_code=404, detail="Skill node not found")

    from database import ResourceCreate

    resource = ResourceCreate(
        skill_node_id=request.skill_node_id,
        title=request.title,
        url=request.url,
        resource_type=request.resource_type,
        source=request.source
    )

    resource_id = db.add_resource(resource)

    return {
        "message": "Resource added",
        "resource_id": resource_id,
        "skill_node_id": request.skill_node_id
    }


@app.get("/api/resources/{node_id}")
def get_node_resources(node_id: int, current_user: dict = Depends(get_current_user)):
    """Get all resources for a skill node"""
    node = db.get_skill_node(node_id, user_id=current_user["id"])
    if not node:
        raise HTTPException(status_code=404, detail="Skill node not found")

    resources = db.get_resources_for_node(node_id)
    return {
        "node_id": node_id,
        "node_name": node["name"],
        "resources": resources
    }


@app.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int):
    """Delete a resource"""
    success = db.delete_resource(resource_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resource not found")
    return {"message": "Resource deleted", "resource_id": resource_id}


# --- Topic Research Endpoint ---

@app.post("/api/research/topic")
async def research_topic(request: TopicResearchRequest, current_user: dict = Depends(get_current_user)):
    """Research a specific topic and add it to the skill tree with subnodes and resources"""
    return await run_topic_research(request, current_user)


async def execute_topic_research_with_streaming(session_id: str, progress_queue: asyncio.Queue, request: TopicResearchRequest, current_user: dict):
    try:
        result = await run_topic_research(request, current_user, progress_queue)
        if result.get("success"):
            event = ProgressEvent(
                type=EventType.TOPIC_COMPLETED,
                timestamp=datetime.utcnow(),
                data=result
            )
        else:
            event = ProgressEvent(
                type=EventType.TOPIC_FAILED,
                timestamp=datetime.utcnow(),
                data={"error": result.get("message", "Topic research failed")}
            )
        await progress_queue.put(event)
    except Exception as e:
        error_event = ProgressEvent(
            type=EventType.TOPIC_FAILED,
            timestamp=datetime.utcnow(),
            data={"error": str(e)}
        )
        await progress_queue.put(error_event)
    finally:
        await asyncio.sleep(2)
        if session_id in active_research_sessions:
            del active_research_sessions[session_id]


@app.post("/api/research/topic/start")
async def start_topic_research_stream(request: TopicResearchRequest, current_user: dict = Depends(get_current_user)):
    """Start topic research with SSE streaming support"""
    session_id = str(uuid.uuid4())
    progress_queue = asyncio.Queue()
    active_research_sessions[session_id] = progress_queue

    asyncio.create_task(execute_topic_research_with_streaming(session_id, progress_queue, request, current_user))

    return {"session_id": session_id, "message": "Topic research started"}


# --- User Preferences Endpoints ---

class PreferencesUpdate(BaseModel):
    target_role: Optional[str] = None
    enabled_sources: Optional[dict] = None
    relevance_threshold: Optional[float] = None
    has_completed_onboarding: Optional[bool] = None


@app.get("/api/preferences")
def get_preferences(current_user: dict = Depends(get_current_user)):
    """Get current user preferences"""
    prefs = db.get_user_preferences(user_id=current_user["id"])
    if not prefs:
        # Return defaults if no preferences exist yet
        return {
            "target_role": "AI Engineer",
            "enabled_sources": {
                "hackernews": True,
                "github_trending": True,
                "devto": True,
                "medium": True,
                "arxiv": True,
                "stackoverflow": True,
                "pypi": True
            },
            "relevance_threshold": 0.5,
            "has_completed_onboarding": False
        }
    return prefs


@app.put("/api/preferences")
def update_preferences(update: PreferencesUpdate, current_user: dict = Depends(get_current_user)):
    """Update user preferences"""
    from database import UserPreferencesCreate

    # Get existing or defaults
    existing = db.get_user_preferences(user_id=current_user["id"])
    if not existing:
        existing = {
            "target_role": "AI Engineer",
            "enabled_sources": {
                "hackernews": True,
                "github_trending": True,
                "devto": True,
                "medium": True,
                "arxiv": True,
                "stackoverflow": True,
                "pypi": True
            },
            "relevance_threshold": 0.5,
            "has_completed_onboarding": False
        }

    # Merge updates
    if update.target_role is not None:
        existing["target_role"] = update.target_role
    if update.enabled_sources is not None:
        existing["enabled_sources"] = update.enabled_sources
    if update.relevance_threshold is not None:
        existing["relevance_threshold"] = update.relevance_threshold
    if update.has_completed_onboarding is not None:
        existing["has_completed_onboarding"] = update.has_completed_onboarding

    prefs = UserPreferencesCreate(
        target_role=existing["target_role"],
        enabled_sources=existing["enabled_sources"],
        relevance_threshold=existing["relevance_threshold"],
        has_completed_onboarding=existing["has_completed_onboarding"]
    )

    db.save_user_preferences(prefs, user_id=current_user["id"])
    return {"message": "Preferences updated", "preferences": existing}


@app.get("/api/preferences/defaults")
def get_preference_defaults():
    """Get available options for preferences"""
    return {
        "available_roles": [
            "AI Engineer",
            "ML Engineer",
            "Data Engineer",
            "Analytics Engineer",
            "Data Scientist",
            "Backend Engineer",
            "Full Stack Engineer"
        ],
        "available_sources": {
            "hackernews": {"name": "Hacker News", "description": "Tech news and discussions"},
            "github_trending": {"name": "GitHub Trending", "description": "Trending repositories"},
            "devto": {"name": "Dev.to", "description": "Developer articles and tutorials"},
            "medium": {"name": "Medium", "description": "Tech blogs and articles"},
            "arxiv": {"name": "ArXiv", "description": "Research papers (AI/ML)"},
            "stackoverflow": {"name": "Stack Overflow", "description": "Q&A trends"},
            "pypi": {"name": "PyPI", "description": "Python packages"}
        },
        "threshold_range": {"min": 0.0, "max": 1.0, "default": 0.5}
    }


# --- Health ---

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
