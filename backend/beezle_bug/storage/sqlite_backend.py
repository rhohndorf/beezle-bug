"""
SQLite storage backend implementation.

Uses aiosqlite for async operations and sqlite-vec for vector similarity search.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import aiosqlite
import sqlite_vec

if TYPE_CHECKING:
    from beezle_bug.project import Project
    from beezle_bug.memory.knowledge_graph import KnowledgeGraph
    from beezle_bug.memory.memories import Observation

from .base import StorageBackend


class SQLiteStorageBackend(StorageBackend):
    """
    SQLite implementation of StorageBackend.
    
    Uses sqlite-vec extension for vector similarity search on observation embeddings.
    """
    
    # Embedding dimension from fastembed
    EMBEDDING_DIM = 384
    
    def __init__(self, db_path: str = "beezle.db"):
        """
        Initialize SQLite backend.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
    
    # === Lifecycle ===
    
    async def initialize(self) -> None:
        """Initialize database connection and create schema."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        
        # Enable foreign keys
        await self._conn.execute("PRAGMA foreign_keys = ON")
        
        # Load sqlite-vec extension
        await self._conn.enable_load_extension(True)
        await self._conn.load_extension(sqlite_vec.loadable_path())
        await self._conn.enable_load_extension(False)
        
        # Create schema
        await self._create_schema()
        await self._conn.commit()
    
    async def _create_schema(self) -> None:
        """Create database tables if they don't exist."""
        await self._conn.executescript("""
            -- Projects table
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                data JSON NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            
            -- Knowledge Graphs (one per KG node in a project)
            CREATE TABLE IF NOT EXISTS knowledge_graphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                node_id TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(project_id, node_id)
            );
            
            -- KG Entities
            CREATE TABLE IF NOT EXISTS kg_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_graph_id INTEGER NOT NULL REFERENCES knowledge_graphs(id) ON DELETE CASCADE,
                entity_name TEXT NOT NULL,
                properties JSON NOT NULL DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(knowledge_graph_id, entity_name)
            );
            
            -- KG Relationships
            CREATE TABLE IF NOT EXISTS kg_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_graph_id INTEGER NOT NULL REFERENCES knowledge_graphs(id) ON DELETE CASCADE,
                from_entity_id INTEGER NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
                to_entity_id INTEGER NOT NULL REFERENCES kg_entities(id) ON DELETE CASCADE,
                rel_type TEXT NOT NULL,
                properties JSON NOT NULL DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            
            -- Index for relationship lookups
            CREATE INDEX IF NOT EXISTS idx_kg_rel_from ON kg_relationships(from_entity_id);
            CREATE INDEX IF NOT EXISTS idx_kg_rel_to ON kg_relationships(to_entity_id);
            CREATE INDEX IF NOT EXISTS idx_kg_rel_type ON kg_relationships(knowledge_graph_id, rel_type);
            
            -- Memory Streams (one per MS node in a project)
            CREATE TABLE IF NOT EXISTS memory_streams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                node_id TEXT NOT NULL,
                last_reflection_point INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(project_id, node_id)
            );
            
            -- Observations
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_stream_id INTEGER NOT NULL REFERENCES memory_streams(id) ON DELETE CASCADE,
                content_type TEXT NOT NULL,
                content JSON NOT NULL,
                importance REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                accessed_at TEXT NOT NULL
            );
            
            -- Index for observation lookups
            CREATE INDEX IF NOT EXISTS idx_obs_stream ON observations(memory_stream_id);
            CREATE INDEX IF NOT EXISTS idx_obs_created ON observations(memory_stream_id, created_at);
        """)
        
        # Create sqlite-vec virtual table for embeddings
        # This needs to be done separately as it's not standard SQL
        try:
            await self._conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS observation_vectors 
                USING vec0(
                    observation_id INTEGER PRIMARY KEY,
                    embedding float[{self.EMBEDDING_DIM}]
                )
            """)
        except Exception:
            # Table might already exist
            pass
    
    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    # === Project Operations ===
    
    async def list_projects(self) -> list[dict]:
        """List all projects with metadata."""
        cursor = await self._conn.execute("""
            SELECT id, name, created_at, updated_at
            FROM projects
            ORDER BY updated_at DESC
        """)
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
    
    async def get_project(self, project_id: str) -> Optional["Project"]:
        """Get a project by ID."""
        from beezle_bug.project import Project
        
        cursor = await self._conn.execute(
            "SELECT data FROM projects WHERE id = ?",
            (project_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        
        data = json.loads(row["data"])
        return Project.model_validate(data)
    
    async def save_project(self, project: "Project") -> None:
        """Save or update a project."""
        data = json.dumps(project.model_dump(mode="json"), default=str)
        await self._conn.execute("""
            INSERT INTO projects (id, name, data, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                data = excluded.data,
                updated_at = datetime('now')
        """, (project.id, project.name, data))
        await self._conn.commit()
    
    async def delete_project(self, project_id: str) -> None:
        """Delete a project and all associated data."""
        # First, delete observation vectors for all observations in this project's memory streams
        await self._conn.execute("""
            DELETE FROM observation_vectors 
            WHERE observation_id IN (
                SELECT o.id FROM observations o
                JOIN memory_streams ms ON o.memory_stream_id = ms.id
                WHERE ms.project_id = ?
            )
        """, (project_id,))
        
        # Cascade delete handles the rest
        await self._conn.execute(
            "DELETE FROM projects WHERE id = ?",
            (project_id,)
        )
        await self._conn.commit()
    
    async def project_exists(self, project_id: str) -> bool:
        """Check if a project exists."""
        cursor = await self._conn.execute(
            "SELECT 1 FROM projects WHERE id = ?",
            (project_id,)
        )
        row = await cursor.fetchone()
        return row is not None
    
    # === Knowledge Graph Operations ===
    
    async def kg_ensure(self, project_id: str, node_id: str) -> int:
        """Ensure a knowledge graph exists, return its ID."""
        # Try to get existing
        cursor = await self._conn.execute(
            "SELECT id FROM knowledge_graphs WHERE project_id = ? AND node_id = ?",
            (project_id, node_id)
        )
        row = await cursor.fetchone()
        if row:
            return row["id"]
        
        # Create new
        cursor = await self._conn.execute("""
            INSERT INTO knowledge_graphs (project_id, node_id)
            VALUES (?, ?)
        """, (project_id, node_id))
        await self._conn.commit()
        return cursor.lastrowid
    
    async def kg_add_entity(
        self,
        kg_id: int,
        entity_name: str,
        properties: dict
    ) -> int:
        """Add an entity to the knowledge graph."""
        props_json = json.dumps(properties)
        cursor = await self._conn.execute("""
            INSERT INTO kg_entities (knowledge_graph_id, entity_name, properties)
            VALUES (?, ?, ?)
        """, (kg_id, entity_name, props_json))
        await self._conn.commit()
        return cursor.lastrowid
    
    async def kg_update_entity(
        self,
        entity_id: int,
        properties: dict
    ) -> None:
        """Update entity properties."""
        props_json = json.dumps(properties)
        await self._conn.execute("""
            UPDATE kg_entities 
            SET properties = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (props_json, entity_id))
        await self._conn.commit()
    
    async def kg_add_entity_property(
        self,
        kg_id: int,
        entity_name: str,
        prop_name: str,
        prop_value: str
    ) -> None:
        """Add or update a single property on an entity."""
        # Get current properties
        cursor = await self._conn.execute("""
            SELECT id, properties FROM kg_entities
            WHERE knowledge_graph_id = ? AND entity_name = ?
        """, (kg_id, entity_name))
        row = await cursor.fetchone()
        if row is None:
            return
        
        properties = json.loads(row["properties"])
        properties[prop_name] = prop_value
        
        await self._conn.execute("""
            UPDATE kg_entities 
            SET properties = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (json.dumps(properties), row["id"]))
        await self._conn.commit()
    
    async def kg_remove_entity_property(
        self,
        kg_id: int,
        entity_name: str,
        prop_name: str
    ) -> None:
        """Remove a property from an entity."""
        cursor = await self._conn.execute("""
            SELECT id, properties FROM kg_entities
            WHERE knowledge_graph_id = ? AND entity_name = ?
        """, (kg_id, entity_name))
        row = await cursor.fetchone()
        if row is None:
            return
        
        properties = json.loads(row["properties"])
        if prop_name in properties:
            del properties[prop_name]
            await self._conn.execute("""
                UPDATE kg_entities 
                SET properties = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (json.dumps(properties), row["id"]))
            await self._conn.commit()
    
    async def kg_remove_entity(self, kg_id: int, entity_name: str) -> None:
        """Remove an entity and all its relationships."""
        # Get entity ID first
        cursor = await self._conn.execute("""
            SELECT id FROM kg_entities
            WHERE knowledge_graph_id = ? AND entity_name = ?
        """, (kg_id, entity_name))
        row = await cursor.fetchone()
        if row is None:
            return
        
        entity_id = row["id"]
        
        # Delete relationships involving this entity
        await self._conn.execute("""
            DELETE FROM kg_relationships
            WHERE from_entity_id = ? OR to_entity_id = ?
        """, (entity_id, entity_id))
        
        # Delete the entity
        await self._conn.execute(
            "DELETE FROM kg_entities WHERE id = ?",
            (entity_id,)
        )
        await self._conn.commit()
    
    async def kg_get_entity_id(self, kg_id: int, entity_name: str) -> Optional[int]:
        """Get the entity ID by name."""
        cursor = await self._conn.execute("""
            SELECT id FROM kg_entities
            WHERE knowledge_graph_id = ? AND entity_name = ?
        """, (kg_id, entity_name))
        row = await cursor.fetchone()
        return row["id"] if row else None
    
    async def kg_add_relationship(
        self,
        kg_id: int,
        from_entity_name: str,
        rel_type: str,
        to_entity_name: str,
        properties: dict
    ) -> int:
        """Add a relationship between two entities."""
        # Get entity IDs
        from_id = await self.kg_get_entity_id(kg_id, from_entity_name)
        to_id = await self.kg_get_entity_id(kg_id, to_entity_name)
        
        if from_id is None or to_id is None:
            raise ValueError(f"Entity not found: {from_entity_name} or {to_entity_name}")
        
        props_json = json.dumps(properties)
        cursor = await self._conn.execute("""
            INSERT INTO kg_relationships 
            (knowledge_graph_id, from_entity_id, to_entity_id, rel_type, properties)
            VALUES (?, ?, ?, ?, ?)
        """, (kg_id, from_id, to_id, rel_type, props_json))
        await self._conn.commit()
        return cursor.lastrowid
    
    async def kg_update_relationship_property(
        self,
        kg_id: int,
        from_entity_name: str,
        rel_type: str,
        to_entity_name: str,
        prop_name: str,
        prop_value: str
    ) -> None:
        """Add or update a property on a relationship."""
        from_id = await self.kg_get_entity_id(kg_id, from_entity_name)
        to_id = await self.kg_get_entity_id(kg_id, to_entity_name)
        
        if from_id is None or to_id is None:
            return
        
        cursor = await self._conn.execute("""
            SELECT id, properties FROM kg_relationships
            WHERE knowledge_graph_id = ? AND from_entity_id = ? 
              AND to_entity_id = ? AND rel_type = ?
        """, (kg_id, from_id, to_id, rel_type))
        row = await cursor.fetchone()
        if row is None:
            return
        
        properties = json.loads(row["properties"])
        properties[prop_name] = prop_value
        
        await self._conn.execute("""
            UPDATE kg_relationships 
            SET properties = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (json.dumps(properties), row["id"]))
        await self._conn.commit()
    
    async def kg_remove_relationship_property(
        self,
        kg_id: int,
        from_entity_name: str,
        rel_type: str,
        to_entity_name: str,
        prop_name: str
    ) -> None:
        """Remove a property from a relationship."""
        from_id = await self.kg_get_entity_id(kg_id, from_entity_name)
        to_id = await self.kg_get_entity_id(kg_id, to_entity_name)
        
        if from_id is None or to_id is None:
            return
        
        cursor = await self._conn.execute("""
            SELECT id, properties FROM kg_relationships
            WHERE knowledge_graph_id = ? AND from_entity_id = ? 
              AND to_entity_id = ? AND rel_type = ?
        """, (kg_id, from_id, to_id, rel_type))
        row = await cursor.fetchone()
        if row is None:
            return
        
        properties = json.loads(row["properties"])
        if prop_name in properties:
            del properties[prop_name]
            await self._conn.execute("""
                UPDATE kg_relationships 
                SET properties = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (json.dumps(properties), row["id"]))
            await self._conn.commit()
    
    async def kg_remove_relationship(
        self,
        kg_id: int,
        from_entity_name: str,
        rel_type: str,
        to_entity_name: str
    ) -> None:
        """Remove a relationship between two entities."""
        from_id = await self.kg_get_entity_id(kg_id, from_entity_name)
        to_id = await self.kg_get_entity_id(kg_id, to_entity_name)
        
        if from_id is None or to_id is None:
            return
        
        await self._conn.execute("""
            DELETE FROM kg_relationships
            WHERE knowledge_graph_id = ? AND from_entity_id = ? 
              AND to_entity_id = ? AND rel_type = ?
        """, (kg_id, from_id, to_id, rel_type))
        await self._conn.commit()
    
    async def kg_load_full(
        self,
        project_id: str,
        node_id: str
    ) -> Optional["KnowledgeGraph"]:
        """Load the full knowledge graph into a KnowledgeGraph instance."""
        from beezle_bug.memory.knowledge_graph import KnowledgeGraph
        
        # Get knowledge graph ID
        cursor = await self._conn.execute(
            "SELECT id FROM knowledge_graphs WHERE project_id = ? AND node_id = ?",
            (project_id, node_id)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        
        kg_id = row["id"]
        kg = KnowledgeGraph()
        
        # Load entities
        cursor = await self._conn.execute("""
            SELECT id, entity_name, properties
            FROM kg_entities
            WHERE knowledge_graph_id = ?
        """, (kg_id,))
        entities = await cursor.fetchall()
        
        entity_id_to_name = {}
        for entity in entities:
            entity_name = entity["entity_name"]
            properties = json.loads(entity["properties"])
            kg.graph.add_node(entity_name, **properties)
            entity_id_to_name[entity["id"]] = entity_name
        
        # Load relationships
        cursor = await self._conn.execute("""
            SELECT from_entity_id, to_entity_id, rel_type, properties
            FROM kg_relationships
            WHERE knowledge_graph_id = ?
        """, (kg_id,))
        relationships = await cursor.fetchall()
        
        for rel in relationships:
            from_name = entity_id_to_name.get(rel["from_entity_id"])
            to_name = entity_id_to_name.get(rel["to_entity_id"])
            if from_name and to_name:
                properties = json.loads(rel["properties"])
                properties["relationship"] = rel["rel_type"]
                kg.graph.add_edge(from_name, to_name, **properties)
        
        return kg
    
    # === Memory Stream Operations ===
    
    async def ms_ensure(self, project_id: str, node_id: str) -> int:
        """Ensure a memory stream exists, return its ID."""
        # Try to get existing
        cursor = await self._conn.execute(
            "SELECT id FROM memory_streams WHERE project_id = ? AND node_id = ?",
            (project_id, node_id)
        )
        row = await cursor.fetchone()
        if row:
            return row["id"]
        
        # Create new
        cursor = await self._conn.execute("""
            INSERT INTO memory_streams (project_id, node_id)
            VALUES (?, ?)
        """, (project_id, node_id))
        await self._conn.commit()
        return cursor.lastrowid
    
    async def ms_add_observation(
        self,
        ms_id: int,
        observation: "Observation"
    ) -> int:
        """Add an observation to the memory stream."""
        content_type = type(observation.content).__name__
        content_json = json.dumps(
            observation.content.model_dump() if hasattr(observation.content, 'model_dump') 
            else observation.content.dict()
        )
        
        # Insert observation
        cursor = await self._conn.execute("""
            INSERT INTO observations 
            (memory_stream_id, content_type, content, importance, created_at, accessed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            ms_id,
            content_type,
            content_json,
            observation.importance,
            observation.created.isoformat(),
            observation.accessed.isoformat()
        ))
        obs_id = cursor.lastrowid
        
        # Insert embedding into vec0 table
        embedding = observation.embedding
        if hasattr(embedding, 'tolist'):
            embedding = embedding.tolist()
        
        await self._conn.execute("""
            INSERT INTO observation_vectors (observation_id, embedding)
            VALUES (?, ?)
        """, (obs_id, sqlite_vec.serialize_float32(embedding)))
        
        await self._conn.commit()
        return obs_id
    
    async def ms_search(
        self,
        ms_id: int,
        query_embedding: list[float],
        k: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list["Observation"]:
        """Search for similar observations using vector similarity."""
        from beezle_bug.memory.memories import Observation
        from beezle_bug.llm_adapter import Message, ToolCallResult, Response
        
        # Build query with optional date filters
        query = """
            SELECT o.id, o.content_type, o.content, o.importance, 
                   o.created_at, o.accessed_at, v.distance
            FROM observations o
            JOIN observation_vectors v ON o.id = v.observation_id
            WHERE o.memory_stream_id = ?
              AND v.embedding MATCH ?
        """
        params = [ms_id, sqlite_vec.serialize_float32(query_embedding)]
        
        if from_date:
            query += " AND o.created_at >= ?"
            params.append(from_date.isoformat())
        
        if to_date:
            query += " AND o.created_at <= ?"
            params.append(to_date.isoformat())
        
        query += f" ORDER BY v.distance LIMIT {k}"
        
        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        
        observations = []
        for row in rows:
            content_type = row["content_type"]
            content_data = json.loads(row["content"])
            
            # Reconstruct content object
            if content_type == "Message":
                content = Message(**content_data)
            elif content_type == "ToolCallResult":
                content = ToolCallResult(**content_data)
            elif content_type == "Response":
                content = Response(**content_data)
            else:
                content = Message(**content_data)
            
            # Get embedding for this observation
            vec_cursor = await self._conn.execute("""
                SELECT embedding FROM observation_vectors 
                WHERE observation_id = ?
            """, (row["id"],))
            vec_row = await vec_cursor.fetchone()
            embedding = sqlite_vec.deserialize_float32(vec_row["embedding"]) if vec_row else []
            
            obs = Observation(
                created=datetime.fromisoformat(row["created_at"]),
                accessed=datetime.fromisoformat(row["accessed_at"]),
                importance=row["importance"],
                embedding=list(embedding),
                content=content
            )
            # Store the database ID for updating accessed timestamp
            obs._db_id = row["id"]
            observations.append(obs)
        
        return observations
    
    async def ms_update_accessed(
        self,
        observation_ids: list[int]
    ) -> None:
        """Update accessed_at timestamp for retrieved observations."""
        if not observation_ids:
            return
        
        placeholders = ",".join("?" * len(observation_ids))
        await self._conn.execute(f"""
            UPDATE observations 
            SET accessed_at = datetime('now')
            WHERE id IN ({placeholders})
        """, observation_ids)
        await self._conn.commit()
    
    async def ms_get_metadata(
        self,
        ms_id: int
    ) -> dict:
        """Get memory stream metadata."""
        cursor = await self._conn.execute(
            "SELECT last_reflection_point FROM memory_streams WHERE id = ?",
            (ms_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return {}
        
        return {
            "last_reflection_point": row["last_reflection_point"]
        }
    
    async def ms_update_metadata(
        self,
        ms_id: int,
        metadata: dict
    ) -> None:
        """Update memory stream metadata."""
        if "last_reflection_point" in metadata:
            await self._conn.execute("""
                UPDATE memory_streams 
                SET last_reflection_point = ?
                WHERE id = ?
            """, (metadata["last_reflection_point"], ms_id))
            await self._conn.commit()






