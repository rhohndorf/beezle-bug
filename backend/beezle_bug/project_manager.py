"""
ProjectManager - manages project lifecycle: create, load, save, close.
"""

from typing import Optional, TYPE_CHECKING
from loguru import logger

from beezle_bug.storage import StorageService
from beezle_bug.project import Project

if TYPE_CHECKING:
    from beezle_bug.agent_graph.runtime import AgentGraphRuntime


class ProjectManager:
    """Manages project lifecycle: create, load, save, close."""

    def __init__(
        self,
        storage: StorageService,
        runtime: "AgentGraphRuntime",
    ):
        self.storage = storage
        self.runtime = runtime
        self.current_project: Optional[Project] = None

    def list_projects(self) -> list[dict]:
        """List all saved projects with metadata."""
        projects = []
        for project_id in self.storage.list_project_ids():
            try:
                project_path = self.storage.get_project_path(project_id)
                project = Project.load(project_path)
                projects.append({
                    "id": project.id,
                    "name": project.name,
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                })
            except Exception as e:
                logger.error(f"Failed to read project {project_id}: {e}")
        return projects

    def create_project(self, name: str) -> Project:
        """Create a new project."""
        project = Project(name=name)
        self.storage.ensure_project_dir(project.id)
        project_path = self.storage.get_project_path(project.id)
        project.save(project_path)
        logger.info(f"Created project: {project.name} ({project.id})")
        return project

    def load_project(self, project_id: str) -> Project:
        """Load a project from disk."""
        # Close current project if any
        if self.current_project:
            self.close_project()

        project_path = self.storage.get_project_path(project_id)
        if not project_path.exists():
            raise FileNotFoundError(f"Project {project_id} not found")

        project = Project.load(project_path)
        self.current_project = project

        logger.info(f"Loaded project: {project.name} ({project.id})")
        return project

    def save_project(self) -> None:
        """Save the current project to disk."""
        if not self.current_project:
            raise ValueError("No project loaded")
        
        self.current_project.touch()
        project_path = self.storage.get_project_path(self.current_project.id)
        self.current_project.save(project_path)
        logger.info(f"Saved project: {self.current_project.name} ({self.current_project.id})")

    def close_project(self) -> None:
        """Close the current project (undeploy first if needed)."""
        if self.runtime.is_deployed:
            self.runtime.undeploy()
        self.current_project = None
        logger.info("Closed project")

    def delete_project(self, project_id: str) -> None:
        """Delete a project from disk."""
        # Close if it's the current project
        if self.current_project and self.current_project.id == project_id:
            self.close_project()

        self.storage.delete_project_dir(project_id)
        logger.info(f"Deleted project: {project_id}")

