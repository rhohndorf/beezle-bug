"""
Project class - container for AgentGraph + settings + metadata.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

from beezle_bug.agent_graph.agent_graph import AgentGraph


class TTSSettings(BaseModel):
    """TTS (voice output) settings for a project."""
    enabled: bool = False
    voice: Optional[str] = None
    speed: float = 1.0
    speaker: int = 0


class STTSettings(BaseModel):
    """STT (voice input) settings for a project."""
    enabled: bool = False
    device_id: Optional[str] = None
    device_label: Optional[str] = None
    wake_words: List[str] = Field(default_factory=lambda: ["hey beezle", "ok beezle"])
    stop_words: List[str] = Field(default_factory=lambda: ["stop listening", "goodbye", "that's all"])
    max_duration: float = 30.0  # Maximum recording duration in seconds


class Project(BaseModel):
    """A project containing an agent graph configuration."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    agent_graph: AgentGraph = Field(default_factory=AgentGraph)
    tts_settings: TTSSettings = Field(default_factory=TTSSettings)
    stt_settings: STTSettings = Field(default_factory=STTSettings)
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
