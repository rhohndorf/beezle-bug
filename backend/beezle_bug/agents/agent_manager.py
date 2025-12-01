"""
Agent Manager for Beezle Bug.

Handles agent lifecycle:
- Creating and destroying agents
- Loading and stopping agents  
- Pausing and resuming agents
- Persistence to/from disk

Filesystem is the source of truth for persisted agents.
Scheduler is the source of truth for autonomous state.
"""

import json
import shutil
from loguru import logger
import uuid
from enum import Enum
from pathlib import Path
from queue import Queue
from typing import Dict, List, Optional, Callable

from beezle_bug.agents import Agent, AgentConfig
from beezle_bug import constants as const
from beezle_bug.exceptions import (
    AgentNotFoundError,
    AgentAlreadyInstancedError,
    AgentNotInstancedError
)
from beezle_bug.llm_adapter import OpenAiAdapter
from beezle_bug.memory import KnowledgeGraph, MemoryStream
from beezle_bug.tools import ToolBox
from beezle_bug.events import EventBus
from beezle_bug.scheduler import Scheduler
from beezle_bug.template import TemplateLoader


class AgentState(Enum):
    """State of an instanced agent."""
    RUNNING = "running"   # In memory, processing messages
    PAUSED = "paused"     # In memory but ignoring messages


class AgentManager:
    """
    Centralized manager for agent lifecycle.
    
    Attributes:
        data_dir: Base directory for agent data storage
        agents: Dictionary of instanced agents (agent_id -> Agent)
        states: Dictionary of agent states (agent_id -> AgentState)
        event_bus: Event bus for agent introspection events
        scheduler: Scheduler for autonomous agent behavior
        toolbox_factory: Factory function to create toolboxes for agents
    """
    
    def __init__(
        self,
        data_dir: Path,
        event_bus: EventBus,
        scheduler: Scheduler,
        toolbox_factory: Callable,
        template_loader: TemplateLoader,
        on_agent_message: Optional[Callable[[str, str, str], None]] = None
    ):
        """
        Initialize the AgentManager.
        
        Args:
            data_dir: Base directory for storing agent data
            event_bus: Event bus for agent events
            scheduler: Scheduler for autonomous behavior
            toolbox_factory: Factory function to create toolboxes
            template_loader: Loader for system message templates
            on_agent_message: Callback for agent messages (agent_id, agent_name, message)
        """
        self.data_dir = Path(data_dir)
        self.agents_dir = self.data_dir / const.AGENT_SUBFOLDER
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory state
        self.agents: Dict[str, Agent] = {}
        self.states: Dict[str, AgentState] = {}
        self.message_queues: Dict[str, Queue] = {}
        
        # Dependencies
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.toolbox_factory = toolbox_factory
        self.template_loader = template_loader
        self.on_agent_message = on_agent_message
    
    # ==================== Query Methods ====================
    
    def list_persisted_agents(self) -> List[dict]:
        """
        Return info about all agents that exist on disk.
        
        Returns:
            List of dicts with agent id and name
        """
        agents = []
        for agent_dir in self.agents_dir.iterdir():
            if agent_dir.is_dir():
                config_path = agent_dir / "config.json"
                if config_path.exists():
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        agents.append({
                            "id": agent_dir.name,
                            "name": config.get("name", "Unknown")
                        })
                    except Exception as e:
                        logger.error(f"Failed to read config for {agent_dir.name}: {e}")
        return agents
    
    def list_instanced_agents(self) -> List[dict]:
        """
        Return info about agents currently in memory.
        
        Returns:
            List of dicts with id, name, state, and autonomousEnabled
        """
        result = []
        for agent_id, agent in self.agents.items():
            result.append({
                "id": agent_id,
                "name": agent.name,
                "state": self.states[agent_id].value,
                "autonomousEnabled": self._is_autonomous_enabled(agent_id)
            })
        return result
    
    def is_instanced(self, agent_id: str) -> bool:
        """Check if an agent is currently in memory."""
        return agent_id in self.agents
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an instanced agent by ID."""
        return self.agents.get(agent_id)
    
    def get_state(self, agent_id: str) -> Optional[AgentState]:
        """Get the state of an instanced agent."""
        return self.states.get(agent_id)
    
    def get_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Load and return config for an agent from disk."""
        return self._load_config(agent_id)
    
    # ==================== Lifecycle Methods ====================
    
    def create_agent(self, config: AgentConfig) -> str:
        """
        Create a new agent, persist config, and load into memory.
        
        Args:
            config: Agent configuration
            
        Returns:
            The new agent's ID
        """
        agent_id = self._generate_id()
        
        # Persist config
        self._save_config(agent_id, config)
        
        # Create and instance the agent
        agent = self._create_agent_instance(agent_id, config)
        self._add_to_memory(agent_id, agent)
        
        logger.info(f"Created agent {agent_id} ({config.name})")
        return agent_id
    
    def load_agent(self, agent_id: str) -> None:
        """
        Load a persisted agent into memory.
        
        Args:
            agent_id: The agent's unique identifier
            
        Raises:
            AgentNotFoundError: If agent doesn't exist on disk
            AgentAlreadyInstancedError: If agent is already in memory
        """
        if agent_id in self.agents:
            raise AgentAlreadyInstancedError(f"Agent {agent_id} is already loaded")
        
        config = self._load_config(agent_id)
        
        # Load persisted state
        knowledge_graph = self._load_knowledge_graph(agent_id) or KnowledgeGraph()
        memory_stream = self._load_memory_stream(agent_id) or MemoryStream()
        
        # Create instance
        agent = self._create_agent_instance(
            agent_id, config,
            knowledge_graph=knowledge_graph,
            memory_stream=memory_stream
        )
        self._add_to_memory(agent_id, agent)
        
        logger.info(f"Loaded agent {agent_id} ({config.name})")
    
    def pause_agent(self, agent_id: str) -> None:
        """
        Pause an agent. It stays in memory but ignores messages.
        Autonomous mode is paused (will resume when agent resumes).
        
        Args:
            agent_id: The agent's unique identifier
            
        Raises:
            AgentNotInstancedError: If agent is not in memory
        """
        if agent_id not in self.agents:
            raise AgentNotInstancedError(f"Agent {agent_id} is not loaded")
        
        self.states[agent_id] = AgentState.PAUSED
        
        # Pause autonomous task if exists (scheduler handles non-existent gracefully)
        self.scheduler.pause_task(f"{agent_id}_autonomous")
        
        logger.info(f"Paused agent {agent_id}")
    
    def resume_agent(self, agent_id: str) -> None:
        """
        Resume a paused agent.
        Autonomous mode is resumed if it was enabled.
        
        Args:
            agent_id: The agent's unique identifier
            
        Raises:
            AgentNotInstancedError: If agent is not in memory
        """
        if agent_id not in self.agents:
            raise AgentNotInstancedError(f"Agent {agent_id} is not loaded")
        
        self.states[agent_id] = AgentState.RUNNING
        
        # Resume autonomous task if exists
        self.scheduler.resume_task(f"{agent_id}_autonomous")
        
        logger.info(f"Resumed agent {agent_id}")
    
    def stop_agent(self, agent_id: str) -> None:
        """
        Persist agent state and remove from memory.
        
        Args:
            agent_id: The agent's unique identifier
            
        Note: No-op if agent is not in memory.
        """
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        
        # Persist state
        self._save_knowledge_graph(agent_id, agent.knowledge_graph)
        self._save_memory_stream(agent_id, agent.memory_stream)
        
        # Cancel autonomous task
        self.scheduler.cancel_task(f"{agent_id}_autonomous")
        
        # Remove from memory
        self._remove_from_memory(agent_id)
        
        logger.info(f"Stopped agent {agent_id}")
    
    def delete_agent(self, agent_id: str) -> None:
        """
        Stop agent (if running) and delete all data from disk.
        
        Args:
            agent_id: The agent's unique identifier
        """
        # Stop without saving (we're deleting anyway)
        if agent_id in self.agents:
            self.scheduler.cancel_task(f"{agent_id}_autonomous")
            self._remove_from_memory(agent_id)
        
        # Delete from disk
        agent_dir = self.agents_dir / agent_id
        if agent_dir.exists():
            shutil.rmtree(agent_dir)
        
        logger.info(f"Deleted agent {agent_id}")
    
    # ==================== Agent Interaction ====================
    
    def process_message(self, agent_id: str, sender: str, message: str) -> Optional[str]:
        """
        Send a message to an agent and get a response.
        
        Args:
            agent_id: The agent's unique identifier
            sender: Name of the message sender
            message: The message content
            
        Returns:
            Agent's response or None if agent is paused/not instanced
        """
        if agent_id not in self.agents:
            return None
        if self.states.get(agent_id) == AgentState.PAUSED:
            logger.debug(f"Agent {agent_id} is paused, ignoring message")
            return None
        
        return self.agents[agent_id].process_message(sender, message)
    
    def trigger_tick(self, agent_id: str, trigger: str = "manual") -> Optional[str]:
        """
        Manually trigger an agent tick.
        
        Args:
            agent_id: The agent's unique identifier
            trigger: Description of what triggered the tick
            
        Returns:
            Agent's response or None if agent is paused/not instanced
        """
        if agent_id not in self.agents:
            return None
        if self.states.get(agent_id) == AgentState.PAUSED:
            logger.debug(f"Agent {agent_id} is paused, ignoring tick")
            return None
        
        return self.agents[agent_id].tick(trigger=trigger)
    
    def process_outgoing_messages(self, agent_id: str) -> None:
        """Process any outgoing messages from an agent's tools."""
        if agent_id not in self.agents:
            return
            
        agent = self.agents[agent_id]
        messages = self.message_queues.get(agent_id)
        
        if messages and self.on_agent_message:
            while not messages.empty():
                msg = messages.get()
                self.on_agent_message(agent_id, agent.name, msg)
    
    # ==================== Autonomous Mode ====================
    
    def enable_autonomous(self, agent_id: str, interval_seconds: float) -> None:
        """
        Enable autonomous mode for an agent.
        
        Args:
            agent_id: The agent's unique identifier
            interval_seconds: Interval between autonomous ticks
            
        Raises:
            AgentNotInstancedError: If agent is not in memory
        """
        if agent_id not in self.agents:
            raise AgentNotInstancedError(f"Agent {agent_id} is not loaded")
        
        agent = self.agents[agent_id]
        task_id = f"{agent_id}_autonomous"
        
        # Cancel existing task if any
        self.scheduler.cancel_task(task_id)
        
        def autonomous_tick():
            """Called by scheduler for autonomous behavior."""
            # Don't run if agent is paused
            if self.states.get(agent_id) == AgentState.PAUSED:
                return
            try:
                logger.info(f"Autonomous tick for agent {agent_id} ({agent.name})")
                response = agent.tick(trigger="autonomous")
                if response and self.on_agent_message:
                    self.on_agent_message(agent_id, agent.name, response)
                    logger.info(f"Agent response: {response[:100]}...")
            except Exception as e:
                logger.error(f"Autonomous tick failed for {agent_id}: {e}")
            
            # Check for outgoing messages from tools
            self.process_outgoing_messages(agent_id)
        
        self.scheduler.schedule_interval(
            task_id=task_id,
            agent_id=agent_id,
            callback=autonomous_tick,
            interval_seconds=interval_seconds,
            start_immediately=False
        )
        
        logger.info(f"Enabled autonomous mode for {agent_id} (every {interval_seconds}s)")
    
    def disable_autonomous(self, agent_id: str) -> None:
        """
        Disable autonomous mode for an agent.
        
        Args:
            agent_id: The agent's unique identifier
        """
        self.scheduler.cancel_task(f"{agent_id}_autonomous")
        logger.info(f"Disabled autonomous mode for {agent_id}")
    
    def set_autonomous(self, agent_id: str, enabled: bool, interval: float = 30) -> None:
        """
        Set autonomous mode for an agent.
        
        Args:
            agent_id: The agent's unique identifier
            enabled: Whether to enable or disable autonomous mode
            interval: Interval between autonomous ticks (if enabling)
        """
        if enabled:
            self.enable_autonomous(agent_id, interval)
        else:
            self.disable_autonomous(agent_id)
    
    def _is_autonomous_enabled(self, agent_id: str) -> bool:
        """Check if autonomous mode is enabled by querying scheduler."""
        task_id = f"{agent_id}_autonomous"
        return task_id in self.scheduler.tasks
    
    # ==================== Private Helpers ====================
    
    @staticmethod
    def _generate_id() -> str:
        """Generate a unique agent ID (8-character UUID)."""
        return str(uuid.uuid4())[:8]
    
    def _get_agent_dir(self, agent_id: str) -> Path:
        """Get the data directory for a specific agent."""
        agent_dir = self.agents_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir
    
    def _add_to_memory(self, agent_id: str, agent: Agent) -> None:
        """Add agent to in-memory tracking."""
        self.agents[agent_id] = agent
        self.states[agent_id] = AgentState.RUNNING
        
        messages = Queue()
        agent.add_contact("Chatroom", messages)
        self.message_queues[agent_id] = messages
    
    def _remove_from_memory(self, agent_id: str) -> None:
        """Remove agent from in-memory tracking."""
        if agent_id in self.agents:
            del self.agents[agent_id]
        if agent_id in self.states:
            del self.states[agent_id]
        if agent_id in self.message_queues:
            del self.message_queues[agent_id]
    
    def _create_agent_instance(
        self,
        agent_id: str,
        config: AgentConfig,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        memory_stream: Optional[MemoryStream] = None
    ) -> Agent:
        """Create an Agent instance from config."""
        adapter = OpenAiAdapter(
            model=config.model,
            api_url=config.apiUrl,
            api_key=config.apiKey
        )
        toolbox = self.toolbox_factory(config.tools)
        system_template = self.template_loader.load(config.systemTemplate)
        
        return Agent(
            id=agent_id,
            name=config.name,
            adapter=adapter,
            toolbox=toolbox,
            event_bus=self.event_bus,
            memory_stream=memory_stream or MemoryStream(),
            knowledge_graph=knowledge_graph or KnowledgeGraph(),
            system_template=system_template
        )
    
    # ==================== Persistence ====================
    
    def _save_config(self, agent_id: str, config: AgentConfig) -> None:
        """Save agent configuration to disk."""
        agent_dir = self._get_agent_dir(agent_id)
        config_path = agent_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config.model_dump(), f, indent=2)
        logger.info(f"Config saved for agent {agent_id}")
    
    def _load_config(self, agent_id: str) -> AgentConfig:
        """Load agent configuration from disk."""
        config_path = self.agents_dir / agent_id / "config.json"
        with open(config_path, 'r') as f:
            data = json.load(f)
        return AgentConfig.model_validate(data)
    
    def _save_knowledge_graph(self, agent_id: str, knowledge_graph: KnowledgeGraph) -> None:
        """Save agent's knowledge graph to disk."""
        agent_dir = self._get_agent_dir(agent_id)
        kg_path = agent_dir / "knowledge_graph.json"
        knowledge_graph.save(str(kg_path))
        logger.info(f"Knowledge graph saved for agent {agent_id}")
    
    def _load_knowledge_graph(self, agent_id: str) -> KnowledgeGraph:
        """Load agent's knowledge graph from disk."""
        kg_path = self.agents_dir / agent_id / "knowledge_graph.json"
        return KnowledgeGraph.load(str(kg_path))
    
    def _save_memory_stream(self, agent_id: str, memory_stream: MemoryStream) -> None:
        """Save agent's memory stream to disk."""
        agent_dir = self._get_agent_dir(agent_id)
        mem_path = agent_dir / "memory_stream.json"
        with open(mem_path, 'w') as f:
            json.dump(memory_stream.to_dict(), f, indent=2)
        logger.info(f"Memory stream saved for agent {agent_id}")
    
    def _load_memory_stream(self, agent_id: str) -> MemoryStream:
        """Load agent's memory stream from disk."""
        mem_path = self.agents_dir / agent_id / "memory_stream.json"
        with open(mem_path, 'r') as f:
            data = json.load(f)
        return MemoryStream.from_dict(data)
    
    # ==================== Cleanup ====================
    
    def shutdown(self) -> None:
        """Shutdown all agents gracefully, saving state."""
        logger.info("Shutting down AgentManager...")
        
        for agent_id in list(self.agents.keys()):
            self.stop_agent(agent_id)
        
        logger.info("AgentManager shutdown complete")
