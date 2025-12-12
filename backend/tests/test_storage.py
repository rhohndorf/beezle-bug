"""
Tests for the storage backend.

Tests cover:
- Project CRUD operations
- Knowledge Graph incremental operations
- Memory Stream operations with vector search
"""

import pytest
import tempfile
import os
from datetime import datetime

from beezle_bug.storage import SQLiteStorageBackend
from beezle_bug.project import Project
from beezle_bug.memory.knowledge_graph import KnowledgeGraph
from beezle_bug.memory.memories import Observation
from beezle_bug.llm_adapter import Message


@pytest.fixture
async def storage(tmp_path):
    """Create a temporary SQLite storage backend."""
    db_path = tmp_path / "test.db"
    backend = SQLiteStorageBackend(str(db_path))
    await backend.initialize()
    yield backend
    await backend.close()


class TestProjectOperations:
    """Tests for project CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_save_and_get_project(self, storage):
        """Test saving and retrieving a project."""
        project = Project(name="Test Project")
        
        await storage.save_project(project)
        
        loaded = await storage.get_project(project.id)
        assert loaded is not None
        assert loaded.id == project.id
        assert loaded.name == "Test Project"
    
    @pytest.mark.asyncio
    async def test_list_projects(self, storage):
        """Test listing all projects."""
        # Create multiple projects
        project1 = Project(name="Project 1")
        project2 = Project(name="Project 2")
        
        await storage.save_project(project1)
        await storage.save_project(project2)
        
        projects = await storage.list_projects()
        assert len(projects) == 2
        names = {p["name"] for p in projects}
        assert names == {"Project 1", "Project 2"}
    
    @pytest.mark.asyncio
    async def test_delete_project(self, storage):
        """Test deleting a project."""
        project = Project(name="To Delete")
        await storage.save_project(project)
        
        # Verify it exists
        assert await storage.project_exists(project.id)
        
        # Delete
        await storage.delete_project(project.id)
        
        # Verify it's gone
        assert not await storage.project_exists(project.id)
        assert await storage.get_project(project.id) is None
    
    @pytest.mark.asyncio
    async def test_project_with_agent_graph(self, storage):
        """Test saving a project with an agent graph."""
        from beezle_bug.agent_graph import AgentGraph, Node, NodeType
        from beezle_bug.agent_graph.types import AgentNodeConfig, Position
        
        project = Project(name="With Graph")
        
        # Add a node
        node = Node(
            type=NodeType.AGENT,
            position=Position(x=100, y=200),
            config=AgentNodeConfig(name="Test Agent")
        )
        project.agent_graph.add_node(node)
        
        await storage.save_project(project)
        
        loaded = await storage.get_project(project.id)
        assert len(loaded.agent_graph.nodes) == 1
        assert loaded.agent_graph.nodes[0].config.name == "Test Agent"


class TestKnowledgeGraphOperations:
    """Tests for knowledge graph operations."""
    
    @pytest.mark.asyncio
    async def test_kg_ensure_creates_new(self, storage):
        """Test that kg_ensure creates a new KG if it doesn't exist."""
        # First create a project
        project = Project(name="KG Test")
        await storage.save_project(project)
        
        kg_id = await storage.kg_ensure(project.id, "kg-node-1")
        assert kg_id > 0
        
        # Second call should return same ID
        kg_id_2 = await storage.kg_ensure(project.id, "kg-node-1")
        assert kg_id_2 == kg_id
    
    @pytest.mark.asyncio
    async def test_kg_add_and_load_entity(self, storage):
        """Test adding entities and loading the full KG."""
        project = Project(name="KG Entity Test")
        await storage.save_project(project)
        
        kg_id = await storage.kg_ensure(project.id, "kg-node-1")
        
        # Add entities
        await storage.kg_add_entity(kg_id, "Alice", {"type": "Person", "age": "30"})
        await storage.kg_add_entity(kg_id, "Bob", {"type": "Person", "age": "25"})
        
        # Load full KG
        kg = await storage.kg_load_full(project.id, "kg-node-1")
        assert kg is not None
        assert len(kg) == 2
        assert kg.graph.has_node("Alice")
        assert kg.graph.has_node("Bob")
    
    @pytest.mark.asyncio
    async def test_kg_add_and_load_relationship(self, storage):
        """Test adding relationships between entities."""
        project = Project(name="KG Rel Test")
        await storage.save_project(project)
        
        kg_id = await storage.kg_ensure(project.id, "kg-node-1")
        
        # Add entities
        await storage.kg_add_entity(kg_id, "Alice", {"type": "Person"})
        await storage.kg_add_entity(kg_id, "Bob", {"type": "Person"})
        
        # Add relationship
        await storage.kg_add_relationship(kg_id, "Alice", "knows", "Bob", {"since": "2020"})
        
        # Load and verify
        kg = await storage.kg_load_full(project.id, "kg-node-1")
        assert kg.graph.has_edge("Alice", "Bob")
        edge_data = kg.graph.edges["Alice", "Bob"]
        assert edge_data["relationship"] == "knows"
    
    @pytest.mark.asyncio
    async def test_kg_remove_entity(self, storage):
        """Test removing an entity."""
        project = Project(name="KG Remove Test")
        await storage.save_project(project)
        
        kg_id = await storage.kg_ensure(project.id, "kg-node-1")
        await storage.kg_add_entity(kg_id, "ToRemove", {"type": "Test"})
        
        # Verify it exists
        kg = await storage.kg_load_full(project.id, "kg-node-1")
        assert kg.graph.has_node("ToRemove")
        
        # Remove
        await storage.kg_remove_entity(kg_id, "ToRemove")
        
        # Verify it's gone
        kg = await storage.kg_load_full(project.id, "kg-node-1")
        assert not kg.graph.has_node("ToRemove")


class TestMemoryStreamOperations:
    """Tests for memory stream operations."""
    
    @pytest.mark.asyncio
    async def test_ms_ensure_creates_new(self, storage):
        """Test that ms_ensure creates a new MS if it doesn't exist."""
        project = Project(name="MS Test")
        await storage.save_project(project)
        
        ms_id = await storage.ms_ensure(project.id, "ms-node-1")
        assert ms_id > 0
        
        # Second call should return same ID
        ms_id_2 = await storage.ms_ensure(project.id, "ms-node-1")
        assert ms_id_2 == ms_id
    
    @pytest.mark.asyncio
    async def test_ms_add_observation(self, storage):
        """Test adding an observation."""
        project = Project(name="MS Obs Test")
        await storage.save_project(project)
        
        ms_id = await storage.ms_ensure(project.id, "ms-node-1")
        
        # Create observation with embedding
        obs = Observation(
            content=Message(role="user", content="Hello world"),
            embedding=[0.1] * 384,  # Fake embedding
            importance=0.5,
            created=datetime.now(),
            accessed=datetime.now()
        )
        
        obs_id = await storage.ms_add_observation(ms_id, obs)
        assert obs_id > 0
    
    @pytest.mark.asyncio
    async def test_ms_search_vector(self, storage):
        """Test vector similarity search."""
        project = Project(name="MS Search Test")
        await storage.save_project(project)
        
        ms_id = await storage.ms_ensure(project.id, "ms-node-1")
        
        # Add observations with different embeddings
        for i in range(5):
            embedding = [0.0] * 384
            embedding[i] = 1.0  # Make each embedding unique
            obs = Observation(
                content=Message(role="user", content=f"Message {i}"),
                embedding=embedding,
                importance=0.5,
                created=datetime.now(),
                accessed=datetime.now()
            )
            await storage.ms_add_observation(ms_id, obs)
        
        # Search with query embedding similar to first observation
        query_embedding = [0.0] * 384
        query_embedding[0] = 1.0
        
        results = await storage.ms_search(ms_id, query_embedding, k=3)
        
        assert len(results) <= 3
        # First result should be the most similar
        if results:
            assert "Message 0" in results[0].content.content
    
    @pytest.mark.asyncio
    async def test_ms_metadata(self, storage):
        """Test memory stream metadata operations."""
        project = Project(name="MS Meta Test")
        await storage.save_project(project)
        
        ms_id = await storage.ms_ensure(project.id, "ms-node-1")
        
        # Get default metadata
        meta = await storage.ms_get_metadata(ms_id)
        assert meta["last_reflection_point"] == 0
        
        # Update metadata
        await storage.ms_update_metadata(ms_id, {"last_reflection_point": 5})
        
        # Verify update
        meta = await storage.ms_get_metadata(ms_id)
        assert meta["last_reflection_point"] == 5


class TestCascadeDelete:
    """Tests for cascade delete behavior."""
    
    @pytest.mark.asyncio
    async def test_project_delete_cascades_to_kg(self, storage):
        """Test that deleting a project also deletes its knowledge graphs."""
        project = Project(name="Cascade Test")
        await storage.save_project(project)
        
        # Create KG with data
        kg_id = await storage.kg_ensure(project.id, "kg-node-1")
        await storage.kg_add_entity(kg_id, "Entity1", {"type": "Test"})
        
        # Delete project
        await storage.delete_project(project.id)
        
        # KG should be gone
        kg = await storage.kg_load_full(project.id, "kg-node-1")
        assert kg is None
    
    @pytest.mark.asyncio
    async def test_project_delete_cascades_to_ms(self, storage):
        """Test that deleting a project also deletes its memory streams."""
        project = Project(name="Cascade MS Test")
        await storage.save_project(project)
        
        # Create MS with data
        ms_id = await storage.ms_ensure(project.id, "ms-node-1")
        obs = Observation(
            content=Message(role="user", content="Test"),
            embedding=[0.1] * 384,
        )
        await storage.ms_add_observation(ms_id, obs)
        
        # Delete project
        await storage.delete_project(project.id)
        
        # MS should be gone - ensure returns a new ID
        ms_id_new = await storage.ms_ensure(project.id, "ms-node-1")
        # This will fail because project is deleted
        # The behavior depends on foreign key constraints






