"""
SQLite storage backend implementation.

Uses SQLModel for project/node/edge ORM operations.
Uses aiosqlite + sqlite-vec for vector similarity search on observation embeddings.
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import aiosqlite
import sqlite_vec
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

if TYPE_CHECKING:
    from beezle_bug.project import Project
    from beezle_bug.memory.knowledge_graph import KnowledgeGraph
    from beezle_bug.memory.memories import Observation

from .base import StorageBackend
from beezle_bug.models import ProjectDB, NodeDB, EdgeDB


class SQLiteStorageBackend(StorageBackend):
    """
    SQLite implementation of StorageBackend.
    
    Uses SQLModel for project CRUD operations.
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
        self._engine = None
        self._session_factory = None
        # Keep aiosqlite connection for sqlite-vec operations
        self._conn: Optional[aiosqlite.Connection] = None
    
    # === Lifecycle ===
    
    async def initialize(self) -> None:
        """Initialize database connection and create schema."""
        # Create SQLAlchemy async engine for SQLModel
        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.db_path}",
            echo=False,
        )
        self._session_factory = async_sessionmaker(
            self._engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        # Create SQLModel tables
        async with self._engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        # Also keep aiosqlite connection for sqlite-vec and legacy operations
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        
        # Enable foreign keys
        await self._conn.execute("PRAGMA foreign_keys = ON")
        
        # Load sqlite-vec extension
        await self._conn.enable_load_extension(True)
        await self._conn.load_extension(sqlite_vec.loadable_path())
        await self._conn.enable_load_extension(False)
        
        # Create additional schema for KG and memory streams
        await self._create_legacy_schema()
        await self._conn.commit()
    
    async def _create_legacy_schema(self) -> None:
        """Create database tables for knowledge graphs and memory streams."""
        await self._conn.executescript("""
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
        """Close database connections."""
        if self._conn:
            await self._conn.close()
            self._conn = None
        if self._engine:
            await self._engine.dispose()
            self._engine = None
    
    # === Project Operations (SQLModel) ===
    
    async def list_projects(self) -> list[dict]:
        """List all projects with metadata."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ProjectDB).order_by(ProjectDB.updated_at.desc())
            )
            projects = result.scalars().all()
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in projects
            ]
    
    async def get_project(self, project_id: str) -> Optional["Project"]:
        """Get a project by ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ProjectDB)
                .options(selectinload(ProjectDB.nodes), selectinload(ProjectDB.edges))
                .where(ProjectDB.id == project_id)
            )
            project_db = result.scalar_one_or_none()
            if project_db is None:
                return None
            return project_db.to_pydantic()
    
    async def save_project(self, project: "Project") -> None:
        """Save or update a project."""
        from sqlalchemy import delete
        
        async with self._session_factory() as session:
            # Check if project exists
            result = await session.execute(
                select(ProjectDB).where(ProjectDB.id == project.id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing project
                existing.name = project.name
                existing.tts_settings = project.tts_settings.model_dump()
                existing.stt_settings = project.stt_settings.model_dump()
                existing.updated_at = datetime.utcnow()
                
                # Delete existing nodes and edges using DELETE statements
                # (avoid lazy-loading relationship access)
                await session.execute(
                    delete(EdgeDB).where(EdgeDB.project_id == project.id)
                )
                await session.execute(
                    delete(NodeDB).where(NodeDB.project_id == project.id)
                )
                
                # Add new nodes and edges
                for node in project.agent_graph.nodes:
                    node_db = NodeDB.from_pydantic(node, project.id)
                    session.add(node_db)
                
                for edge in project.agent_graph.edges:
                    edge_db = EdgeDB.from_pydantic(edge, project.id)
                    session.add(edge_db)
            else:
                # Create new project
                project_db = ProjectDB.from_pydantic(project)
                session.add(project_db)
                
                # Add nodes
                for node in project.agent_graph.nodes:
                    node_db = NodeDB.from_pydantic(node, project.id)
                    session.add(node_db)
                
                # Add edges
                for edge in project.agent_graph.edges:
                    edge_db = EdgeDB.from_pydantic(edge, project.id)
                    session.add(edge_db)
            
            await session.commit()
    
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
        await self._conn.commit()
        
        # Delete project (cascade handles nodes, edges)
        async with self._session_factory() as session:
            result = await session.execute(
                select(ProjectDB).where(ProjectDB.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project:
                await session.delete(project)
                await session.commit()
        
        # Delete KG and memory stream data
        await self._conn.execute(
            "DELETE FROM knowledge_graphs WHERE project_id = ?",
            (project_id,)
        )
        await self._conn.execute(
            "DELETE FROM memory_streams WHERE project_id = ?",
            (project_id,)
        )
        await self._conn.commit()
    
    async def project_exists(self, project_id: str) -> bool:
        """Check if a project exists."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ProjectDB.id).where(ProjectDB.id == project_id)
            )
            return result.scalar_one_or_none() is not None
    
    # === Knowledge Graph Operations (aiosqlite) ===
    
    async def kg_ensure(self, project_id: str, node_id: str) -> int:
        """Ensure a knowledge graph exists, return its ID."""
        cursor = await self._conn.execute(
            "SELECT id FROM knowledge_graphs WHERE project_id = ? AND node_id = ?",
            (project_id, node_id)
        )
        row = await cursor.fetchone()
        if row:
            return row["id"]
        
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
        cursor = await self._conn.execute("""
            SELECT id FROM kg_entities
            WHERE knowledge_graph_id = ? AND entity_name = ?
        """, (kg_id, entity_name))
        row = await cursor.fetchone()
        if row is None:
            return
        
        entity_id = row["id"]
        
        await self._conn.execute("""
            DELETE FROM kg_relationships
            WHERE from_entity_id = ? OR to_entity_id = ?
        """, (entity_id, entity_id))
        
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
    
    # === Memory Stream Operations (aiosqlite) ===
    
    async def ms_ensure(self, project_id: str, node_id: str) -> int:
        """Ensure a memory stream exists, return its ID."""
        cursor = await self._conn.execute(
            "SELECT id FROM memory_streams WHERE project_id = ? AND node_id = ?",
            (project_id, node_id)
        )
        row = await cursor.fetchone()
        if row:
            return row["id"]
        
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
            
            if content_type == "Message":
                content = Message(**content_data)
            elif content_type == "ToolCallResult":
                content = ToolCallResult(**content_data)
            elif content_type == "Response":
                content = Response(**content_data)
            else:
                content = Message(**content_data)
            
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
    
    async def ms_get_recent(
        self,
        ms_id: int,
        n: int
    ) -> list["Observation"]:
        """Get the N most recent observations for a memory stream (chronological order)."""
        import json
        from beezle_bug.memory.memories import Observation
        from beezle_bug.llm_adapter import Message, ToolCallResult, Response
        
        cursor = await self._conn.execute("""
            SELECT id, content_type, content, importance, created_at, accessed_at
            FROM observations 
            WHERE memory_stream_id = ?
            ORDER BY created_at DESC 
            LIMIT ?
        """, (ms_id, n))
        rows = await cursor.fetchall()
        
        observations = []
        for row in rows:
            content_type = row["content_type"]
            content_data = json.loads(row["content"])
            
            # Reconstruct the content object
            if content_type == "ToolCallResult":
                content = ToolCallResult(**content_data)
            elif content_type == "Response":
                content = Response(**content_data)
            else:
                content = Message(**content_data)
            
            obs = Observation(
                created=datetime.fromisoformat(row["created_at"]),
                accessed=datetime.fromisoformat(row["accessed_at"]),
                importance=row["importance"],
                embedding=[],  # Not needed for recent retrieval
                content=content
            )
            obs._db_id = row["id"]
            observations.append(obs)
        
        # Reverse to get chronological order (oldest first)
        observations.reverse()
        return observations
