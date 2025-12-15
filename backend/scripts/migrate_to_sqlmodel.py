#!/usr/bin/env python3
"""
Migration script to convert old JSON-blob projects to new SQLModel schema.

Run this script after updating to the SQLModel-based storage backend.
It will:
1. Read projects from the old 'data' JSON column
2. Create new records in the projects, nodes, and edges tables
3. Remove the old 'data' column (or leave it for backup)

Usage:
    python -m scripts.migrate_to_sqlmodel [--db-path /path/to/beezle.db]
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import aiosqlite


async def check_migration_needed(db_path: str) -> bool:
    """Check if migration is needed by looking for old 'data' column."""
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("PRAGMA table_info(projects)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # If 'data' column exists, migration might be needed
        if 'data' in column_names:
            # Check if there are projects with data but no corresponding nodes
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM projects 
                WHERE data IS NOT NULL AND data != '{}'
            """)
            count = (await cursor.fetchone())[0]
            return count > 0
        return False


async def migrate_projects(db_path: str, dry_run: bool = False):
    """Migrate projects from old JSON schema to new normalized schema."""
    print(f"Opening database: {db_path}")
    
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Check for old schema
        cursor = await conn.execute("PRAGMA table_info(projects)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'data' not in column_names:
            print("No 'data' column found - database may already be migrated or is new.")
            return
        
        # Get all projects with data
        cursor = await conn.execute("""
            SELECT id, name, data, created_at, updated_at FROM projects
            WHERE data IS NOT NULL AND data != '{}'
        """)
        projects = await cursor.fetchall()
        
        if not projects:
            print("No projects with data to migrate.")
            return
        
        print(f"Found {len(projects)} project(s) to migrate.")
        
        for project in projects:
            project_id = project["id"]
            project_name = project["name"]
            
            try:
                data = json.loads(project["data"])
            except json.JSONDecodeError:
                print(f"  WARNING: Could not parse JSON for project {project_id}")
                continue
            
            print(f"\nMigrating project: {project_name} ({project_id})")
            
            # Extract settings
            tts_settings = data.get("tts_settings", {})
            stt_settings = data.get("stt_settings", {})
            agent_graph = data.get("agent_graph", {})
            nodes = agent_graph.get("nodes", [])
            edges = agent_graph.get("edges", [])
            
            print(f"  - {len(nodes)} nodes, {len(edges)} edges")
            print(f"  - TTS: {tts_settings.get('enabled', False)}, STT: {stt_settings.get('enabled', False)}")
            
            if dry_run:
                print("  [DRY RUN] Would migrate this project")
                continue
            
            # Check if nodes table has entries for this project
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM nodes WHERE project_id = ?",
                (project_id,)
            )
            existing_nodes = (await cursor.fetchone())[0]
            
            if existing_nodes > 0:
                print(f"  Project already has {existing_nodes} nodes in new schema, skipping...")
                continue
            
            # Update project with settings columns
            await conn.execute("""
                UPDATE projects 
                SET tts_settings = ?, stt_settings = ?
                WHERE id = ?
            """, (json.dumps(tts_settings), json.dumps(stt_settings), project_id))
            
            # Insert nodes
            for node in nodes:
                node_id = node.get("id")
                node_type = node.get("type")
                position = node.get("position", {})
                config = node.get("config", {})
                
                await conn.execute("""
                    INSERT OR IGNORE INTO nodes (id, project_id, type, position_x, position_y, config)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    node_id,
                    project_id,
                    node_type,
                    position.get("x", 0),
                    position.get("y", 0),
                    json.dumps(config)
                ))
            
            # Insert edges
            for edge in edges:
                edge_id = edge.get("id")
                source_node = edge.get("source_node")
                source_port = edge.get("source_port")
                target_node = edge.get("target_node")
                target_port = edge.get("target_port")
                edge_type = edge.get("edge_type")
                
                await conn.execute("""
                    INSERT OR IGNORE INTO edges 
                    (id, project_id, source_node_id, source_port, target_node_id, target_port, edge_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    edge_id,
                    project_id,
                    source_node,
                    source_port,
                    target_node,
                    target_port,
                    edge_type
                ))
            
            print(f"  Migrated successfully!")
        
        if not dry_run:
            await conn.commit()
            print("\nMigration complete!")
            print("\nThe 'data' column has been left in place as a backup.")
            print("You can remove it manually after verifying the migration:")
            print("  ALTER TABLE projects DROP COLUMN data;")


async def main():
    parser = argparse.ArgumentParser(description="Migrate Beezle Bug database to SQLModel schema")
    parser.add_argument(
        "--db-path",
        default="/data/beezle.db",
        help="Path to the SQLite database file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    args = parser.parse_args()
    
    db_path = args.db_path
    
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        print("Make sure to run this from the container or provide the correct path.")
        sys.exit(1)
    
    needs_migration = await check_migration_needed(db_path)
    if not needs_migration:
        print("No migration needed - database is already in new format or empty.")
        return
    
    await migrate_projects(db_path, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())

