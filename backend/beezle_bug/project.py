"""
Project class - container for AgentGraph + settings + metadata.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, model_validator

from beezle_bug.agent_graph.types import TTSSettings
from beezle_bug.agent_graph.agent_graph import AgentGraph


class Project(BaseModel):
    """A project containing an agent graph configuration."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    agent_graph: AgentGraph = Field(default_factory=AgentGraph)
    tts_settings: TTSSettings = Field(default_factory=TTSSettings)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode='before')
    @classmethod
    def migrate_mesh_to_agent_graph(cls, data):
        """Backward compatibility: convert 'mesh' key to 'agent_graph'."""
        if isinstance(data, dict) and 'mesh' in data and 'agent_graph' not in data:
            data['agent_graph'] = data.pop('mesh')
        return data

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    # Persistence methods

    def save(self, path: Path) -> None:
        """Save the project to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, default=str)

    @classmethod
    def load(cls, path: Path) -> "Project":
        """Load a project from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.model_validate(data)
