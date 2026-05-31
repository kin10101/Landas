#!/usr/bin/env python3
"""
Landas Skill Tree CLI

Commands:
    python tree_cli.py generate <role>      Generate skill tree for a role
    python tree_cli.py list                  List all skill trees
    python tree_cli.py view <role_id>        View a skill tree
    python tree_cli.py export <role_id>      Export tree as JSON
    python tree_cli.py progress <node_id> <status>  Set node status (completed/in_progress/removed)
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from database import Database, NodeStatus
from skill_tree_generator import SkillTreeGenerator, generate_default_trees


def print_tree(node, indent=0, show_resources=False):
    """Pretty print a skill tree"""
    prefix = "  " * indent
    status_icon = ""

    progress = node.get("progress")
    if progress:
        status = progress.get("status", "active")
        if status == "completed":
            status_icon = "[x]"
        elif status == "in_progress":
            status_icon = "[>]"
        elif status == "removed":
            status_icon = "[-]"
        else:
            status_icon = "[ ]"
    else:
        status_icon = "[ ]"

    level = node.get("level", "")
    difficulty = "*" * node.get("difficulty", 1)

    print(f"{prefix}{status_icon} {node['name']} ({level}) {difficulty}")

    if node.get("description"):
        print(f"{prefix}    {node['description'][:80]}")

    if show_resources and node.get("resources"):
        for res in node["resources"][:3]:
            print(f"{prefix}    -> {res['title']}: {res['url'][:50]}")

    for child in node.get("children", []):
        print_tree(child, indent + 1, show_resources)


def cmd_generate(args, db):
    """Generate a skill tree for a role"""
    generator = SkillTreeGenerator(db)
    root_id = generator.generate_tree(args.role)

    if root_id:
        print(f"\n[+] Generated skill tree with ID: {root_id}")
        print("\nTree structure:")
        tree = db.get_full_tree(root_id)
        print_tree(tree)
    else:
        print("[!] Failed to generate skill tree")


def cmd_generate_defaults(args, db):
    """Generate default skill trees for all roles"""
    roots = generate_default_trees(db)
    print(f"\n[+] Generated {len(roots)} default skill trees")
    for root in roots:
        print(f"  - {root['name']} (ID: {root['id']})")


def cmd_list(args, db):
    """List all skill trees"""
    roots = db.get_root_nodes()

    if not roots:
        print("No skill trees found. Generate one with: python tree_cli.py generate <role>")
        return

    print("\n[*] Available Skill Trees:")
    print("-" * 50)
    for root in roots:
        children = db.get_children(root["id"])
        print(f"  ID: {root['id']} | {root['name']} | Categories: {len(children)}")


def cmd_view(args, db):
    """View a skill tree"""
    tree = db.get_full_tree(args.role_id)

    if not tree:
        print(f"[!] Skill tree with ID {args.role_id} not found")
        return

    print(f"\n[*] Skill Tree: {tree['name']}")
    print("=" * 60)
    print_tree(tree, show_resources=args.resources)


def cmd_export(args, db):
    """Export tree as JSON"""
    tree = db.get_full_tree(args.role_id)

    if not tree:
        print(f"[!] Skill tree with ID {args.role_id} not found")
        return

    filename = f"skill_tree_{tree['name'].lower().replace(' ', '_')}.json"
    with open(filename, "w") as f:
        json.dump(tree, f, indent=2, default=str)

    print(f"[+] Exported to {filename}")


def cmd_progress(args, db):
    """Set progress on a node"""
    status_map = {
        "completed": NodeStatus.COMPLETED,
        "in_progress": NodeStatus.IN_PROGRESS,
        "removed": NodeStatus.REMOVED,
        "active": NodeStatus.ACTIVE,
    }

    if args.status not in status_map:
        print(f"[!] Invalid status. Use: {', '.join(status_map.keys())}")
        return

    node = db.get_skill_node(args.node_id)
    if not node:
        print(f"[!] Node with ID {args.node_id} not found")
        return

    db.set_user_progress(args.node_id, status_map[args.status])
    print(f"[+] Set '{node['name']}' to {args.status}")


def cmd_discoveries(args, db):
    """Show discovered technologies"""
    discoveries = db.get_all_discoveries()

    if not discoveries:
        print("No discoveries yet. Run the research agent first.")
        return

    print(f"\n[*] Discovered Technologies ({len(discoveries)} total)")
    print("-" * 60)

    for d in discoveries[:20]:
        trend = d.get("trend", "stable")
        emerging = "NEW" if d.get("is_emerging") else "EST"
        print(f"  [{emerging}] {d['name']} ({d['category']}) - {trend} - seen {d['mention_count']}x")


def main():
    parser = argparse.ArgumentParser(description="Landas Skill Tree CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate skill tree for a role")
    gen_parser.add_argument("role", type=str, help="Role name (e.g., 'AI Engineer')")

    # Generate defaults command
    subparsers.add_parser("generate-defaults", help="Generate default skill trees for all roles")

    # List command
    subparsers.add_parser("list", help="List all skill trees")

    # View command
    view_parser = subparsers.add_parser("view", help="View a skill tree")
    view_parser.add_argument("role_id", type=int, help="Role ID from list command")
    view_parser.add_argument("--resources", "-r", action="store_true", help="Show resources")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export tree as JSON")
    export_parser.add_argument("role_id", type=int, help="Role ID from list command")

    # Progress command
    prog_parser = subparsers.add_parser("progress", help="Set node progress status")
    prog_parser.add_argument("node_id", type=int, help="Node ID")
    prog_parser.add_argument("status", type=str, help="Status: completed, in_progress, removed, active")

    # Discoveries command
    subparsers.add_parser("discoveries", help="Show discovered technologies")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize database
    db = Database("landas.db")

    try:
        if args.command == "generate":
            cmd_generate(args, db)
        elif args.command == "generate-defaults":
            cmd_generate_defaults(args, db)
        elif args.command == "list":
            cmd_list(args, db)
        elif args.command == "view":
            cmd_view(args, db)
        elif args.command == "export":
            cmd_export(args, db)
        elif args.command == "progress":
            cmd_progress(args, db)
        elif args.command == "discoveries":
            cmd_discoveries(args, db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
