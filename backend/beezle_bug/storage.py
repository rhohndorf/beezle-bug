"""
StorageService - file I/O abstraction for projects and node data.
"""

import json
import shutil
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from beezle_bug.memory.knowledge_graph import KnowledgeGraph
    from beezle_bug.memory.memory_stream import MemoryStream


class StorageService:
    """Handles all file I/O for projects and node data."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.projects_dir = data_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    # === Project Directory Operations ===

    def get_project_dir(self, project_id: str) -> Path:
        """Get the directory for a project."""
        return self.projects_dir / project_id

    def get_project_path(self, project_id: str) -> Path:
        """Get the path to a project's JSON file."""
        return self.get_project_dir(project_id) / "project.json"

    def list_project_ids(self) -> list[str]:
        """List all project IDs (directory names)."""
        project_ids = []
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                config_path = project_dir / "project.json"
                if config_path.exists():
                    project_ids.append(project_dir.name)
        return project_ids

    def project_exists(self, project_id: str) -> bool:
        """Check if a project exists."""
        return self.get_project_path(project_id).exists()

    def ensure_project_dir(self, project_id: str) -> Path:
        """Ensure a project directory exists and return its path."""
        project_dir = self.get_project_dir(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def delete_project_dir(self, project_id: str) -> None:
        """Delete a project directory and all its contents."""
        project_dir = self.get_project_dir(project_id)
        if project_dir.exists():
            shutil.rmtree(project_dir)
            logger.info(f"Deleted project directory: {project_id}")

    # === Node Data Directory Operations ===

    def get_node_data_dir(self, project_id: str, node_id: str) -> Path:
        """Get the data directory for a node."""
        node_dir = self.get_project_dir(project_id) / "nodes" / node_id
        node_dir.mkdir(parents=True, exist_ok=True)
        return node_dir

    def get_node_data_path(self, project_id: str, node_id: str, filename: str) -> Path:
        """Get the path for a node's data file."""
        return self.get_node_data_dir(project_id, node_id) / filename

    # === Knowledge Graph Persistence ===

    def save_knowledge_graph(self, project_id: str, node_id: str, kg: "KnowledgeGraph") -> None:
        """Save a knowledge graph to disk."""
        kg_path = self.get_node_data_path(project_id, node_id, "knowledge_graph.json")
        kg.save(str(kg_path))
        logger.debug(f"Saved knowledge graph for node {node_id}")

    def load_knowledge_graph(self, project_id: str, node_id: str) -> Optional["KnowledgeGraph"]:
        """Load a knowledge graph from disk if it exists."""
        from beezle_bug.memory.knowledge_graph import KnowledgeGraph
        
        kg_path = self.get_node_data_path(project_id, node_id, "knowledge_graph.json")
        if not kg_path.exists():
            return None
        
        kg = KnowledgeGraph.load(str(kg_path))
        logger.debug(f"Loaded knowledge graph for node {node_id}")
        return kg

    # === Memory Stream Persistence ===

    def save_memory_stream(self, project_id: str, node_id: str, ms: "MemoryStream") -> None:
        """Save a memory stream to disk."""
        from beezle_bug.memory.memory_stream import MemoryStream
        
        ms_path = self.get_node_data_path(project_id, node_id, "memory_stream.json")
        with open(ms_path, "w") as f:
            json.dump(ms.to_dict(), f, indent=2)
        logger.debug(f"Saved memory stream for node {node_id}")

    def load_memory_stream(self, project_id: str, node_id: str) -> Optional["MemoryStream"]:
        """Load a memory stream from disk if it exists."""
        from beezle_bug.memory.memory_stream import MemoryStream
        
        ms_path = self.get_node_data_path(project_id, node_id, "memory_stream.json")
        if not ms_path.exists():
            return None
        
        with open(ms_path, "r") as f:
            data = json.load(f)
        ms = MemoryStream.from_dict(data)
        logger.debug(f"Loaded memory stream for node {node_id}")
        return ms

