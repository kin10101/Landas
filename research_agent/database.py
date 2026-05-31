"""
Database models for Landas skill graph and research tracking

Schema:
- SkillNode: Hierarchical skill tree (4 levels: Role -> Category -> Skill -> SubSkill)
- Resource: Learning resources linked to skill nodes
- ResearchRun: Historical research run tracking
- TechDiscovery: Technologies discovered by the research agent
- UserProgress: User's progress on skill nodes (completed, removed, in-progress)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class NodeLevel(str, Enum):
    ROLE = "role"           # Level 0: AI Engineer, Data Engineer
    CATEGORY = "category"   # Level 1: LLMs, Data Pipelines
    SKILL = "skill"         # Level 2: RAG, ETL
    SUBSKILL = "subskill"   # Level 3: Vector DBs, Airflow DAGs


class NodeStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    REMOVED = "removed"
    IN_PROGRESS = "in_progress"


class TrendDirection(str, Enum):
    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"
    EMERGING = "emerging"


# Pydantic models for data transfer
class SkillNodeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    level: NodeLevel
    parent_id: Optional[int] = None
    difficulty: int = 1  # 1-5
    relevance_score: float = 0.5
    trend: TrendDirection = TrendDirection.STABLE
    user_id: int = 1


class ResourceCreate(BaseModel):
    skill_node_id: int
    title: str
    url: str
    resource_type: str  # tutorial, docs, article, video, course
    source: Optional[str] = None


class UserPreferencesCreate(BaseModel):
    target_role: str = "AI Engineer"
    enabled_sources: dict = {
        "hackernews": True,
        "github_trending": True,
        "devto": True,
        "medium": True,
        "arxiv": True,
        "stackoverflow": True,
        "pypi": True
    }
    relevance_threshold: float = 0.5
    has_completed_onboarding: bool = False


class Database:
    """SQLite database manager for Landas"""

    def __init__(self, db_path: str = "landas.db"):
        self.db_path = Path(db_path)
        self.conn = None
        self._init_db()

    def _init_db(self):
        """Initialize database with schema"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._migrate_user_progress()
        self._migrate_skill_nodes_user_id()

    def _create_tables(self):
        """Create all tables"""
        cursor = self.conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

        # Skill nodes table (hierarchical tree)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                level TEXT NOT NULL,
                parent_id INTEGER,
                difficulty INTEGER DEFAULT 1,
                relevance_score REAL DEFAULT 0.5,
                trend TEXT DEFAULT 'stable',
                position_x REAL DEFAULT 0,
                position_y REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES skill_nodes(id) ON DELETE CASCADE
            )
        """)

        # Resources table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_node_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                source TEXT,
                quality_score REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (skill_node_id) REFERENCES skill_nodes(id) ON DELETE CASCADE
            )
        """)

        # Research runs table (historical tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                target_roles TEXT NOT NULL,
                sources_used TEXT,
                total_items_collected INTEGER DEFAULT 0,
                technologies_found INTEGER DEFAULT 0,
                execution_time_seconds REAL DEFAULT 0,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Technology discoveries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tech_discoveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                research_run_id INTEGER,
                name TEXT NOT NULL,
                category TEXT,
                description TEXT,
                relevance_score REAL DEFAULT 0.5,
                trend TEXT DEFAULT 'stable',
                source TEXT,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mention_count INTEGER DEFAULT 1,
                is_emerging BOOLEAN DEFAULT 1,
                is_deprecated BOOLEAN DEFAULT 0,
                replacement TEXT,
                FOREIGN KEY (research_run_id) REFERENCES research_runs(id)
            )
        """)

        # User progress table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_node_id INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                notes TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (skill_node_id) REFERENCES skill_nodes(id) ON DELETE CASCADE,
                UNIQUE(skill_node_id)
            )
        """)

        # Skill dependencies table (edges between nodes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_dependencies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_skill_id INTEGER NOT NULL,
                to_skill_id INTEGER NOT NULL,
                dependency_type TEXT DEFAULT 'prerequisite',
                FOREIGN KEY (from_skill_id) REFERENCES skill_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (to_skill_id) REFERENCES skill_nodes(id) ON DELETE CASCADE,
                UNIQUE(from_skill_id, to_skill_id)
            )
        """)

        # User preferences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                target_role TEXT NOT NULL DEFAULT 'AI Engineer',
                enabled_sources TEXT NOT NULL DEFAULT '{}',
                relevance_threshold REAL DEFAULT 0.5,
                has_completed_onboarding INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)

        # Index for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_skill_parent ON skill_nodes(parent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tech_name ON tech_discoveries(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resource_skill ON resources(skill_node_id)")

        self.conn.commit()

    def _migrate_user_progress(self):
        """Add user_id column to user_progress if missing (safe migration)"""
        cursor = self.conn.cursor()

        # Check if user_id column exists
        cursor.execute("PRAGMA table_info(user_progress)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'user_id' not in columns:
            # Create new table with user_id
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_progress_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    skill_node_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'active',
                    notes TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (skill_node_id) REFERENCES skill_nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, skill_node_id)
                )
            """)

            # Copy existing data (default user_id=1 for existing records)
            cursor.execute("""
                INSERT OR IGNORE INTO user_progress_new
                (id, user_id, skill_node_id, status, notes, started_at, completed_at, updated_at)
                SELECT id, 1, skill_node_id, status, notes, started_at, completed_at, updated_at
                FROM user_progress
            """)

            # Replace old table
            cursor.execute("DROP TABLE user_progress")
            cursor.execute("ALTER TABLE user_progress_new RENAME TO user_progress")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_progress(user_id)")

            self.conn.commit()

    def _migrate_skill_nodes_user_id(self):
        """Add user_id column to skill_nodes if missing (safe migration)"""
        cursor = self.conn.cursor()

        cursor.execute("PRAGMA table_info(skill_nodes)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'user_id' not in columns:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_nodes_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    name TEXT NOT NULL,
                    description TEXT,
                    level TEXT NOT NULL,
                    parent_id INTEGER,
                    difficulty INTEGER DEFAULT 1,
                    relevance_score REAL DEFAULT 0.5,
                    trend TEXT DEFAULT 'stable',
                    position_x REAL DEFAULT 0,
                    position_y REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES skill_nodes_new(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            cursor.execute("""
                INSERT INTO skill_nodes_new
                (id, user_id, name, description, level, parent_id, difficulty, relevance_score, trend, position_x, position_y, created_at, updated_at)
                SELECT id, 1, name, description, level, parent_id, difficulty, relevance_score, trend, position_x, position_y, created_at, updated_at
                FROM skill_nodes
            """)

            cursor.execute("DROP TABLE skill_nodes")
            cursor.execute("ALTER TABLE skill_nodes_new RENAME TO skill_nodes")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_skill_nodes_user ON skill_nodes(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_skill_parent ON skill_nodes(parent_id)")

            self.conn.commit()

    # --- User Operations ---

    def create_user(self, email: str, password_hash: str, name: str = None) -> int:
        """Create a new user"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO users (email, password_hash, name)
            VALUES (?, ?, ?)
        """, (email, password_hash, name))
        self.conn.commit()
        return cursor.lastrowid

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Get user by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result["created_at"] = str(result["created_at"]) if result["created_at"] else None
            return result
        return None

    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result["created_at"] = str(result["created_at"]) if result["created_at"] else None
            return result
        return None

    # --- Skill Node Operations ---

    def create_skill_node(self, node: SkillNodeCreate) -> int:
        """Create a new skill node"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO skill_nodes (user_id, name, description, level, parent_id, difficulty, relevance_score, trend)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (node.user_id, node.name, node.description, node.level.value, node.parent_id,
              node.difficulty, node.relevance_score, node.trend.value))
        self.conn.commit()
        return cursor.lastrowid

    def get_skill_node(self, node_id: int, user_id: int = None) -> Optional[dict]:
        """Get a skill node by ID, optionally filtered by user"""
        cursor = self.conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT * FROM skill_nodes WHERE id = ? AND user_id = ?", (node_id, user_id))
        else:
            cursor.execute("SELECT * FROM skill_nodes WHERE id = ?", (node_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_node_position(self, node_id: int, x: float, y: float):
        """Update node position for drag and drop"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE skill_nodes SET position_x = ?, position_y = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (x, y, node_id)
        )
        self.conn.commit()

    def get_children(self, parent_id: int, user_id: int = None) -> List[dict]:
        """Get all children of a skill node"""
        cursor = self.conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT * FROM skill_nodes WHERE parent_id = ? AND user_id = ?", (parent_id, user_id))
        else:
            cursor.execute("SELECT * FROM skill_nodes WHERE parent_id = ?", (parent_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_root_nodes(self, user_id: int = None) -> List[dict]:
        """Get all root nodes (roles), optionally filtered by user"""
        cursor = self.conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT * FROM skill_nodes WHERE parent_id IS NULL AND user_id = ?", (user_id,))
        else:
            cursor.execute("SELECT * FROM skill_nodes WHERE parent_id IS NULL")
        return [dict(row) for row in cursor.fetchall()]

    def get_full_tree(self, root_id: int = None, user_id: int = 1) -> dict:
        """Get full skill tree as nested dict, filtered by user"""
        def build_tree(node_id):
            node = self.get_skill_node(node_id, user_id)
            if not node:
                return None
            node["children"] = [build_tree(child["id"]) for child in self.get_children(node_id, user_id)]
            node["resources"] = self.get_resources_for_node(node_id)
            node["progress"] = self.get_user_progress(node_id, user_id)
            return node

        if root_id:
            return build_tree(root_id)

        roots = self.get_root_nodes(user_id)
        return {"roles": [build_tree(r["id"]) for r in roots]}

    def update_skill_node(self, node_id: int, **kwargs) -> bool:
        """Update a skill node"""
        if not kwargs:
            return False
        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [node_id]
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE skill_nodes SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_skill_node(self, node_id: int, user_id: int = None) -> bool:
        """Delete a skill node and its children, optionally checking ownership"""
        cursor = self.conn.cursor()
        if user_id is not None:
            cursor.execute("DELETE FROM skill_nodes WHERE id = ? AND user_id = ?", (node_id, user_id))
        else:
            cursor.execute("DELETE FROM skill_nodes WHERE id = ?", (node_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # --- Resource Operations ---

    def add_resource(self, resource: ResourceCreate) -> int:
        """Add a resource to a skill node"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO resources (skill_node_id, title, url, resource_type, source)
            VALUES (?, ?, ?, ?, ?)
        """, (resource.skill_node_id, resource.title, resource.url,
              resource.resource_type, resource.source))
        self.conn.commit()
        return cursor.lastrowid

    def get_resources_for_node(self, skill_node_id: int) -> List[dict]:
        """Get all resources for a skill node"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE skill_node_id = ?", (skill_node_id,))
        return [dict(row) for row in cursor.fetchall()]

    def delete_resource(self, resource_id: int) -> bool:
        """Delete a resource by ID"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM resources WHERE id = ?", (resource_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # --- Research Run Operations ---

    def save_research_run(self, run_id: str, target_roles: List[str], sources: List[str],
                          items_collected: int, techs_found: int, exec_time: float) -> int:
        """Save a research run"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO research_runs (run_id, target_roles, sources_used, total_items_collected,
                                       technologies_found, execution_time_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (run_id, ",".join(target_roles), ",".join(sources),
              items_collected, techs_found, exec_time))
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_runs(self, limit: int = 10) -> List[dict]:
        """Get recent research runs"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM research_runs ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

    # --- Technology Discovery Operations ---

    def save_tech_discovery(self, name: str, category: str, description: str,
                            relevance: float, trend: str, source: str,
                            is_emerging: bool, research_run_id: int = None) -> int:
        """Save a discovered technology (or update if exists)"""
        cursor = self.conn.cursor()

        # Check if already exists
        cursor.execute("SELECT id, mention_count FROM tech_discoveries WHERE name = ?", (name,))
        existing = cursor.fetchone()

        if existing:
            # Update existing
            cursor.execute("""
                UPDATE tech_discoveries
                SET mention_count = mention_count + 1,
                    last_seen_at = CURRENT_TIMESTAMP,
                    relevance_score = ?,
                    trend = ?
                WHERE id = ?
            """, (relevance, trend, existing["id"]))
            self.conn.commit()
            return existing["id"]
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO tech_discoveries (name, category, description, relevance_score,
                                             trend, source, is_emerging, research_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, category, description, relevance, trend, source, is_emerging, research_run_id))
            self.conn.commit()
            return cursor.lastrowid

    def get_all_discoveries(self, emerging_only: bool = False) -> List[dict]:
        """Get all discovered technologies"""
        cursor = self.conn.cursor()
        if emerging_only:
            cursor.execute("SELECT * FROM tech_discoveries WHERE is_emerging = 1 ORDER BY last_seen_at DESC")
        else:
            cursor.execute("SELECT * FROM tech_discoveries ORDER BY last_seen_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_discovery_by_name(self, name: str) -> Optional[dict]:
        """Check if a technology has already been discovered"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM tech_discoveries WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # --- User Progress Operations ---

    def set_user_progress(self, skill_node_id: int, status: NodeStatus, notes: str = None, user_id: int = 1) -> int:
        """Set user progress on a skill node"""
        cursor = self.conn.cursor()

        completed_at = datetime.now().isoformat() if status == NodeStatus.COMPLETED else None
        started_at = datetime.now().isoformat() if status == NodeStatus.IN_PROGRESS else None

        cursor.execute("""
            INSERT INTO user_progress (user_id, skill_node_id, status, notes, started_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, skill_node_id) DO UPDATE SET
                status = excluded.status,
                notes = excluded.notes,
                completed_at = excluded.completed_at,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, skill_node_id, status.value, notes, started_at, completed_at))
        self.conn.commit()
        return cursor.lastrowid

    def get_user_progress(self, skill_node_id: int, user_id: int = 1) -> Optional[dict]:
        """Get user progress for a skill node"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_progress WHERE skill_node_id = ? AND user_id = ?", (skill_node_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_completed_skills(self) -> List[dict]:
        """Get all completed skills"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT sn.*, up.status, up.completed_at
            FROM skill_nodes sn
            JOIN user_progress up ON sn.id = up.skill_node_id
            WHERE up.status = 'completed'
        """)
        return [dict(row) for row in cursor.fetchall()]

    # --- User Preferences Operations ---

    def get_user_preferences(self, user_id: int = 1) -> Optional[dict]:
        """Get user preferences"""
        import json
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result["enabled_sources"] = json.loads(result["enabled_sources"]) if result["enabled_sources"] else {}
            result["has_completed_onboarding"] = bool(result["has_completed_onboarding"])
            return result
        return None

    def save_user_preferences(self, prefs: UserPreferencesCreate, user_id: int = 1) -> int:
        """Save or update user preferences"""
        import json
        cursor = self.conn.cursor()
        enabled_sources_json = json.dumps(prefs.enabled_sources)

        cursor.execute("""
            INSERT INTO user_preferences (user_id, target_role, enabled_sources, relevance_threshold, has_completed_onboarding)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                target_role = excluded.target_role,
                enabled_sources = excluded.enabled_sources,
                relevance_threshold = excluded.relevance_threshold,
                has_completed_onboarding = excluded.has_completed_onboarding,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, prefs.target_role, enabled_sources_json, prefs.relevance_threshold, int(prefs.has_completed_onboarding)))
        self.conn.commit()
        return cursor.lastrowid

    def has_completed_onboarding(self, user_id: int = 1) -> bool:
        """Check if user has completed onboarding"""
        prefs = self.get_user_preferences(user_id)
        return prefs.get("has_completed_onboarding", False) if prefs else False

    # --- Utility ---

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
