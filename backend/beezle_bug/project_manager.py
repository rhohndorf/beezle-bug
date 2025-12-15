"""
ProjectManager - manages project lifecycle: create, load, save, close.

All operations are async to work with the database storage backend.
"""

from typing import TYPE_CHECKING, Optional
from loguru import logger

from beezle_bug.project import Project

if TYPE_CHECKING:
    from beezle_bug.storage.base import StorageBackend
    from beezle_bug.agent_graph.runtime import AgentGraphRuntime


class ProjectManager:
    """Manages project lifecycle: create, load, save, close."""

    def __init__(
        self,
        storage: "StorageBackend",
        runtime: "AgentGraphRuntime",
    ):
        self.storage = storage
        self.runtime = runtime
        self.current_project: Optional[Project] = None

    async def list_projects(self) -> list[dict]:
        """List all saved projects with metadata."""
        return await self.storage.list_projects()

    async def create_project(self, name: str) -> Project:
        """Create a new project."""
        project = Project(name=name)
        await self.storage.save_project(project)
        logger.info(f"Created project: {project.name} ({project.id})")
        return project

    async def load_project(self, project_id: str) -> Project:
        """Load a project from database."""
        # Close current project if any
        if self.current_project:
            await self.close_project()

        project = await self.storage.get_project(project_id)
        if project is None:
            raise FileNotFoundError(f"Project {project_id} not found")

        self.current_project = project
        logger.info(f"Loaded project: {project.name} ({project.id})")
        return project

    async def save_project(self) -> None:
        """Save the current project to database."""
        if not self.current_project:
            raise ValueError("No project loaded")
        
        self.current_project.touch()
        await self.storage.save_project(self.current_project)
        logger.info(f"Saved project: {self.current_project.name} ({self.current_project.id})")

    async def close_project(self) -> None:
        """Close the current project (undeploy first if needed)."""
        if self.runtime.is_deployed:
            await self.runtime.undeploy()
        self.current_project = None
        logger.info("Closed project")

    async def delete_project(self, project_id: str) -> None:
        """Delete a project from database."""
        # Close if it's the current project
        if self.current_project and self.current_project.id == project_id:
            await self.close_project()

        await self.storage.delete_project(project_id)
        logger.info(f"Deleted project: {project_id}")
