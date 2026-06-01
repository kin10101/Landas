"""
Skill Tree Generator

Auto-generates a complete skill tree for a given role using OpenAI.
Tree structure: Role -> Category -> Skill -> SubSkill (4 levels)
"""

import json
import os
import sys
from typing import List, Optional
from openai import OpenAI
from langsmith.wrappers import wrap_openai
from langsmith import traceable

# Handle imports for both direct execution and import from other modules
try:
    from .database import Database, SkillNodeCreate, ResourceCreate, NodeLevel, TrendDirection
except ImportError:
    from database import Database, SkillNodeCreate, ResourceCreate, NodeLevel, TrendDirection


class SkillTreeGenerator:
    """Generates complete skill trees for career roles"""

    def __init__(self, db: Database, user_id: int = 1):
        self.client = wrap_openai(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.db = db
        self.user_id = user_id

    def generate_tree(self, role: str, user_id: int = None) -> int:
        """Generate a complete skill tree for a role

        Returns:
            Root node ID of the generated tree
        """
        if user_id is None:
            user_id = self.user_id

        print(f"\n[*] Generating skill tree for: {role} (user_id={user_id})")

        # Generate the tree structure with OpenAI
        tree_structure = self._generate_structure(role)

        if not tree_structure:
            print(f"[!] Failed to generate tree structure for {role}")
            return None

        # Save to database
        root_id = self._save_tree_to_db(tree_structure, role, user_id)

        print(f"[+] Skill tree generated with root ID: {root_id}")
        return root_id

    @traceable(name="generate_tree_structure")
    def _generate_structure(self, role: str) -> dict:
        """Use OpenAI to generate the tree structure"""

        prompt = f"""
Generate a comprehensive skill tree for the role: {role}

The tree should have 4 levels:
1. Role (root) - The main career role
2. Categories - Major skill categories (5-8 categories)
3. Skills - Specific skills within each category (3-6 per category)
4. Sub-skills - Detailed sub-skills or tools (2-4 per skill)

For each node, provide:
- name: Clear, concise name
- description: Brief description (1-2 sentences)
- difficulty: 1-5 (1=beginner, 5=expert)
- resources: Array of learning resources (title, url, type)

Return ONLY valid JSON in this exact structure:
{{
    "role": "{role}",
    "description": "Role description",
    "categories": [
        {{
            "name": "Category Name",
            "description": "Category description",
            "difficulty": 2,
            "skills": [
                {{
                    "name": "Skill Name",
                    "description": "Skill description",
                    "difficulty": 3,
                    "resources": [
                        {{"title": "Resource Title", "url": "https://...", "type": "docs"}}
                    ],
                    "subskills": [
                        {{
                            "name": "Sub-skill Name",
                            "description": "Sub-skill description",
                            "difficulty": 4,
                            "resources": []
                        }}
                    ]
                }}
            ]
        }}
    ]
}}

Make sure the tree is:
1. Comprehensive but focused on the most important skills
2. Ordered from foundational to advanced within each category
3. Includes real, working URLs for resources (official docs, tutorials)
4. Relevant to current industry standards (2024-2025)

Generate the tree for: {role}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )

            text = response.choices[0].message.content

            # Extract JSON
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                json_str = text.strip()

            return json.loads(json_str)

        except Exception as e:
            print(f"[!] Error generating tree structure: {str(e)}")
            return None

    def _save_tree_to_db(self, tree: dict, role: str, user_id: int) -> int:
        """Save generated tree to database"""

        # Create root node (role)
        root = SkillNodeCreate(
            name=tree.get("role", role),
            description=tree.get("description", ""),
            level=NodeLevel.ROLE,
            difficulty=1,
            relevance_score=1.0,
            trend=TrendDirection.STABLE,
            user_id=user_id
        )
        root_id = self.db.create_skill_node(root)

        # Create categories
        for cat in tree.get("categories", []):
            cat_node = SkillNodeCreate(
                name=cat["name"],
                description=cat.get("description", ""),
                level=NodeLevel.CATEGORY,
                parent_id=root_id,
                difficulty=cat.get("difficulty", 2),
                relevance_score=0.8,
                trend=TrendDirection.STABLE,
                user_id=user_id
            )
            cat_id = self.db.create_skill_node(cat_node)

            # Create skills
            for skill in cat.get("skills", []):
                skill_node = SkillNodeCreate(
                    name=skill["name"],
                    description=skill.get("description", ""),
                    level=NodeLevel.SKILL,
                    parent_id=cat_id,
                    difficulty=skill.get("difficulty", 3),
                    relevance_score=0.7,
                    trend=TrendDirection.STABLE,
                    user_id=user_id
                )
                skill_id = self.db.create_skill_node(skill_node)

                # Add resources for skill
                for resource in skill.get("resources", []):
                    try:
                        res = ResourceCreate(
                            skill_node_id=skill_id,
                            title=resource.get("title", ""),
                            url=resource.get("url", ""),
                            resource_type=resource.get("type", "docs"),
                            source="AI Generated"
                        )
                        self.db.add_resource(res)
                    except:
                        pass

                # Create sub-skills
                for subskill in skill.get("subskills", []):
                    sub_node = SkillNodeCreate(
                        name=subskill["name"],
                        description=subskill.get("description", ""),
                        level=NodeLevel.SUBSKILL,
                        parent_id=skill_id,
                        difficulty=subskill.get("difficulty", 4),
                        relevance_score=0.6,
                        trend=TrendDirection.STABLE,
                        user_id=user_id
                    )
                    sub_id = self.db.create_skill_node(sub_node)

                    # Add resources for sub-skill
                    for resource in subskill.get("resources", []):
                        try:
                            res = ResourceCreate(
                                skill_node_id=sub_id,
                                title=resource.get("title", ""),
                                url=resource.get("url", ""),
                                resource_type=resource.get("type", "docs"),
                                source="AI Generated"
                            )
                            self.db.add_resource(res)
                        except:
                            pass

        return root_id

    def enrich_with_research(self, root_id: int, discoveries: List[dict], user_id: int = None):
        """Enrich existing tree with research discoveries

        Adds new technologies and resources found by research agent
        """
        if user_id is None:
            user_id = self.user_id

        print(f"\n[*] Enriching skill tree with {len(discoveries)} discoveries...")

        # Get the tree
        tree = self.db.get_full_tree(root_id, user_id)
        if not tree:
            print("[!] Tree not found")
            return

        # Find matching skills and add resources
        for discovery in discoveries:
            self._add_discovery_to_tree(tree, discovery)

        print("[+] Tree enrichment complete")

    def _add_discovery_to_tree(self, tree: dict, discovery: dict):
        """Add a discovery as a resource to matching skills"""
        # This is a simplified matching - in production you'd use embeddings
        discovery_name = discovery.get("name", "").lower()
        discovery_category = discovery.get("category", "").lower()

        def search_and_add(node):
            node_name = node.get("name", "").lower()

            # Check if discovery matches this node
            if discovery_name in node_name or node_name in discovery_name:
                # Add as resource
                try:
                    res = ResourceCreate(
                        skill_node_id=node["id"],
                        title=f"Learn {discovery.get('name', '')}",
                        url=f"https://google.com/search?q={discovery.get('name', '').replace(' ', '+')}+tutorial",
                        resource_type="tutorial",
                        source="Research Agent"
                    )
                    self.db.add_resource(res)
                except:
                    pass

            # Search children
            for child in node.get("children", []):
                search_and_add(child)

        search_and_add(tree)


def generate_default_trees(db: Database, user_id: int = 1):
    """Generate default skill trees for common roles"""
    generator = SkillTreeGenerator(db, user_id=user_id)

    default_roles = [
        "AI Engineer",
        "Data Engineer",
        "ML Engineer",
        "Analytics Engineer"
    ]

    for role in default_roles:
        # Check if role already exists for this user
        existing = db.get_root_nodes(user_id)
        if any(n["name"] == role for n in existing):
            print(f"[*] Skill tree for '{role}' already exists for user {user_id}, skipping...")
            continue

        generator.generate_tree(role, user_id)

    return db.get_root_nodes(user_id)
