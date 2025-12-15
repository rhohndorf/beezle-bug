"""
WebSocket server for Beezle Bug using FastAPI + python-socketio.

Handles:
- Agent lifecycle management via AgentManager
- Chat messages
- Scheduler for autonomous agent behavior
- Event forwarding for introspection
"""

import os
import base64
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from loguru import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from beezle_bug import constants as const
from beezle_bug.events import EventBus
from beezle_bug.scheduler import Scheduler
from beezle_bug.template import TemplateLoader
from beezle_bug.tools.toolbox_factory import ToolboxFactory
from beezle_bug.storage import get_storage_backend
from beezle_bug.project_manager import ProjectManager
from beezle_bug.agent_graph import (
    AgentGraphRuntime,
    Node,
    Edge,
    NodeType,
    EdgeType,
    Position,
    AgentNodeConfig,
    KnowledgeGraphNodeConfig,
    MemoryStreamNodeConfig,
    ToolboxNodeConfig,
    TextInputNodeConfig,
    VoiceInputNodeConfig,
    TextOutputNodeConfig,
    ScheduledEventNodeConfig,
    WaitAndCombineNodeConfig,
)
from beezle_bug.project import TTSSettings, STTSettings
from beezle_bug.voice.tts import PiperTTS, get_tts, PIPER_AVAILABLE


# Data directory for persistence
DATA_DIR = Path(os.environ.get("BEEZLE_DATA_DIR", const.DEFAULT_DATA_DIR))
DB_BACKEND = os.environ.get("BEEZLE_DB_BACKEND", "sqlite")

# Global components (initialized in lifespan)
event_bus: EventBus = None
scheduler: Scheduler = None
toolbox_factory: ToolboxFactory = None
template_loader: TemplateLoader = None
storage = None
runtime: AgentGraphRuntime = None
project_manager: ProjectManager = None

# TTS State
tts_enabled = False
tts_instance: Optional[PiperTTS] = None

# Per-session client preferences
_client_preferences = {}  # sid -> {"tts_enabled": bool}


def event_handler(event):
    """Forward agent events to connected clients."""
    try:
        asyncio.create_task(sio.emit('agent_event', event.to_dict()))
    except Exception as e:
        logger.error(f"Failed to emit event: {e}")


async def on_agent_graph_message(agent_id: str, agent_name: str, message: str):
    """Callback for agent graph messages from scheduled events etc."""
    msg_data = {
        "agentId": agent_id,
        "user": agent_name,
        "message": message,
        "source": "agent_graph"
    }
    await sio.emit("chat_message", msg_data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize and cleanup resources."""
    global event_bus, scheduler, toolbox_factory, template_loader
    global storage, runtime, project_manager
    
    logger.info("Initializing Beezle Bug server...")
    
    # Initialize components
    event_bus = EventBus()
    scheduler = Scheduler(tick_interval=1.0)
    toolbox_factory = ToolboxFactory()
    template_loader = TemplateLoader(DATA_DIR)
    
    # Initialize storage backend
    db_path = DATA_DIR / "beezle.db"
    storage = await get_storage_backend(DB_BACKEND, db_path=str(db_path))
    
    # Initialize runtime and project manager
    runtime = AgentGraphRuntime(
        storage=storage,
        event_bus=event_bus,
        scheduler=scheduler,
        template_loader=template_loader,
        toolbox_factory=toolbox_factory,
        on_agent_graph_message=lambda aid, name, msg: asyncio.create_task(
            on_agent_graph_message(aid, name, msg)
        ),
    )
    
    project_manager = ProjectManager(storage=storage, runtime=runtime)
    
    # Subscribe to all events
    event_bus.subscribe_all(event_handler)
    
    # Start scheduler
    scheduler.start()
    
    logger.info(f"Server initialized. Data directory: {DATA_DIR}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Beezle Bug server...")
    scheduler.stop()
    await storage.close()


# Create FastAPI app
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create async Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
)
socket_app = socketio.ASGIApp(sio, app)


# ==================== Helper Functions ====================

def _build_agent_graph_state() -> dict:
    """Build the current agent graph state for the frontend."""
    if not project_manager.current_project:
        return {"nodes": [], "edges": [], "is_deployed": False}

    project = project_manager.current_project
    return {
        "project_id": project.id,
        "project_name": project.name,
        "is_deployed": runtime.is_deployed,
        "nodes": [
            {
                "id": node.id,
                "type": node.type.value,
                "position": {"x": node.position.x, "y": node.position.y},
                "config": node.config.model_dump(),
                "ports": node.get_ports(),
            }
            for node in project.agent_graph.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "source_node": edge.source_node,
                "source_port": edge.source_port,
                "target_node": edge.target_node,
                "target_port": edge.target_port,
                "edge_type": edge.edge_type.value,
            }
            for edge in project.agent_graph.edges
        ],
    }


# ==================== Socket.IO Event Handlers ====================

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    _client_preferences.pop(sid, None)
    logger.info(f"Client disconnected: {sid}")


# ==================== Tools & Templates ====================

@sio.event
async def get_tools(sid):
    """Get all available tools and presets."""
    await sio.emit("tools_list", {
        "tools": toolbox_factory.list_tools(),
        "presets": {
            name: toolbox_factory.get_preset(name) 
            for name in toolbox_factory.list_presets()
        }
    }, room=sid)


@sio.event
async def get_templates(sid):
    """Get all available system message templates."""
    await sio.emit("templates_list", {
        "templates": template_loader.list_templates()
    }, room=sid)


@sio.event
async def get_template_content(sid, data):
    """Get the raw content of a specific template."""
    name = data.get("name")
    if not name:
        await sio.emit("error", {"message": "Template name required"}, room=sid)
        return
    
    try:
        content = template_loader.get_content(name)
        await sio.emit("template_content", {
            "name": name,
            "content": content
        }, room=sid)
    except FileNotFoundError as e:
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def save_template(sid, data):
    """Create or update a template file."""
    name = data.get("name")
    content = data.get("content")
    
    if not name:
        await sio.emit("error", {"message": "Template name required"}, room=sid)
        return
    if content is None:
        await sio.emit("error", {"message": "Template content required"}, room=sid)
        return
    
    try:
        template_loader.save(name, content)
        await sio.emit("template_saved", {"name": name}, room=sid)
        await sio.emit("log", {"type": "success", "message": f"Template saved: {name}"})
        await sio.emit("templates_list", {"templates": template_loader.list_templates()}, room=sid)
    except Exception as e:
        logger.error(f"Failed to save template: {e}")
        await sio.emit("error", {"message": f"Failed to save template: {e}"}, room=sid)


@sio.event
async def delete_template(sid, data):
    """Delete a template file."""
    name = data.get("name")
    if not name:
        await sio.emit("error", {"message": "Template name required"}, room=sid)
        return
    
    try:
        template_loader.delete(name)
        await sio.emit("template_deleted", {"name": name}, room=sid)
        await sio.emit("log", {"type": "success", "message": f"Template deleted: {name}"})
        await sio.emit("templates_list", {"templates": template_loader.list_templates()}, room=sid)
    except FileNotFoundError as e:
        await sio.emit("error", {"message": str(e)}, room=sid)
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        await sio.emit("error", {"message": f"Failed to delete template: {e}"}, room=sid)


# ==================== Chat ====================

@sio.event
async def send_message(sid, data):
    """Handle chat messages from users."""
    global tts_instance
    
    logger.info(f"Message from {sid}: {data}")
    await sio.emit("chat_message", data, room=sid)  # Echo user message to sender
    # Force event loop to flush the socket buffer before starting agent processing
    await asyncio.sleep(0.01)
    
    user = data.get("user", "User")
    message = data.get("message", "")
    
    # If an agent graph project is active, route through it
    if project_manager.current_project and runtime.agents:
        responses = await runtime.send_user_message(message, user)
        
        for resp in responses:
            logger.debug(f"Agent graph response from {resp['agent_name']}: {resp['response'][:50]}...")
            
            # Check this client's TTS preference
            prefs = _client_preferences.get(sid, {})
            if prefs.get("tts_enabled") and tts_instance is not None:
                try:
                    audio_bytes = tts_instance.synthesize(resp["response"])
                    if audio_bytes:
                        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                        await sio.emit("tts_audio", {
                            "audioUrl": f"data:audio/wav;base64,{audio_b64}"
                        }, room=sid)
                        logger.info(f"Generated TTS audio for client {sid}: {len(audio_bytes)} bytes")
                except Exception as e:
                    logger.error(f"TTS synthesis failed: {e}")


@sio.event
async def send_voice_message(sid, data):
    """Handle voice-transcribed messages from users (routes through VoiceInput node)."""
    global tts_instance
    
    logger.info(f"Voice message from {sid}: {data}")
    # Broadcast user message to ALL clients immediately (before agent processing)
    await sio.emit("chat_message", data)
    # Force event loop to flush the socket buffer before starting agent processing
    await asyncio.sleep(0.01)
    logger.debug(f"Broadcasted voice message to all clients")
    
    user = data.get("user", "User")
    message = data.get("message", "")
    
    # If an agent graph project is active, route through voice input node
    if project_manager.current_project and runtime.agents:
        responses = await runtime.send_voice_message(message, user)
        
        for resp in responses:
            logger.debug(f"Agent graph response from {resp['agent_name']}: {resp['response'][:50]}...")
            
            # Check this client's TTS preference
            prefs = _client_preferences.get(sid, {})
            if prefs.get("tts_enabled") and tts_instance is not None:
                try:
                    audio_bytes = tts_instance.synthesize(resp["response"])
                    if audio_bytes:
                        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                        await sio.emit("tts_audio", {
                            "audioUrl": f"data:audio/wav;base64,{audio_b64}"
                        }, room=sid)
                        logger.info(f"Generated TTS audio for client {sid}: {len(audio_bytes)} bytes")
                except Exception as e:
                    logger.error(f"TTS synthesis failed: {e}")


# ==================== Schedule ====================

@sio.event
async def get_schedule(sid):
    """Get all scheduled tasks."""
    tasks = []
    for task_id, task in scheduler.tasks.items():
        tasks.append({
            "id": task.id,
            "agent_id": task.agent_id,
            "trigger_type": task.trigger_type.value,
            "enabled": task.enabled,
            "run_count": task.run_count,
            "interval_seconds": task.interval_seconds if task.trigger_type.value == "interval" else None,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "run_at": task.run_at.isoformat() if task.run_at else None
        })
    await sio.emit("schedule_update", {"tasks": tasks}, room=sid)


@sio.event
async def pause_schedule_task(sid, data):
    """Pause a scheduled task."""
    task_id = data.get("taskId")
    if task_id:
        scheduler.pause_task(task_id)
        await get_schedule(sid)


@sio.event
async def resume_schedule_task(sid, data):
    """Resume a paused task."""
    task_id = data.get("taskId")
    if task_id:
        scheduler.resume_task(task_id)
        await get_schedule(sid)


@sio.event
async def cancel_schedule_task(sid, data):
    """Cancel a scheduled task."""
    task_id = data.get("taskId")
    if task_id:
        scheduler.cancel_task(task_id)
        await get_schedule(sid)


# ==================== Project Management ====================

@sio.event
async def list_projects(sid):
    """List all saved projects."""
    projects = await project_manager.list_projects()
    await sio.emit("projects_list", {"projects": projects}, room=sid)


@sio.event
async def create_project(sid, data):
    """Create a new project."""
    name = data.get("name", "Untitled Project")
    try:
        project = await project_manager.create_project(name)
        await sio.emit("project_created", {
            "id": project.id,
            "name": project.name,
        }, room=sid)
        await list_projects(sid)
        await sio.emit("log", {"type": "success", "message": f"Project '{name}' created"})
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def load_project(sid, data):
    """Load a project and instantiate its agent graph."""
    global tts_enabled, tts_instance
    
    project_id = data.get("id")
    if not project_id:
        return
    
    try:
        project = await project_manager.load_project(project_id)
        
        # Restore TTS settings from project
        tts_settings = project.tts_settings
        tts_enabled = tts_settings.enabled
        if tts_instance is None and tts_enabled:
            tts_instance = get_tts()
        if tts_instance is not None:
            if tts_settings.voice:
                tts_instance.set_voice(tts_settings.voice)
            tts_instance.set_speed(tts_settings.speed)
            tts_instance.set_speaker(tts_settings.speaker)
        
        await sio.emit("project_loaded", {
            "id": project.id,
            "name": project.name,
            "tts_settings": {
                "enabled": tts_settings.enabled,
                "voice": tts_settings.voice,
                "speed": tts_settings.speed,
                "speaker": tts_settings.speaker,
            }
        }, room=sid)
        await sio.emit("agent_graph_state", _build_agent_graph_state(), room=sid)
        await get_tts_settings(sid)
        await sio.emit("log", {"type": "success", "message": f"Project '{project.name}' loaded"})
    except FileNotFoundError:
        await sio.emit("error", {"message": f"Project {project_id} not found"}, room=sid)
    except Exception as e:
        logger.error(f"Failed to load project: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def save_project(sid):
    """Save the current project with current TTS settings."""
    global tts_enabled, tts_instance
    
    try:
        # Update project TTS settings before saving
        if project_manager.current_project:
            project_manager.current_project.tts_settings = TTSSettings(
                enabled=tts_enabled,
                voice=tts_instance.current_voice_name if tts_instance else None,
                speed=tts_instance.speed if tts_instance else 1.0,
                speaker=tts_instance.speaker if tts_instance else 0,
            )
        
        await project_manager.save_project()
        await sio.emit("log", {"type": "success", "message": "Project saved"})
    except ValueError as e:
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def deploy_project(sid):
    """Deploy the current project - instantiate all agents and resources."""
    try:
        if not project_manager.current_project:
            await sio.emit("error", {"message": "No project loaded"}, room=sid)
            return
        
        await runtime.deploy(
            project_manager.current_project.agent_graph,
            project_manager.current_project.id
        )
        await sio.emit("agent_graph_state", _build_agent_graph_state())
        await sio.emit("agent_graph_agents", runtime.get_running_agents())
        await sio.emit("log", {"type": "success", "message": f"Project deployed: {project_manager.current_project.name}"})
    except Exception as e:
        import traceback
        logger.error(f"Failed to deploy project: {e}\n{traceback.format_exc()}")
        await sio.emit("error", {"message": str(e) or "Unknown error during deployment"}, room=sid)


@sio.event
async def undeploy_project(sid):
    """Undeploy the current project - stop all agents and resources."""
    try:
        await runtime.undeploy()
        await sio.emit("agent_graph_state", _build_agent_graph_state())
        await sio.emit("agent_graph_agents", [])
        await sio.emit("log", {"type": "success", "message": "Project undeployed"})
    except Exception as e:
        logger.error(f"Failed to undeploy project: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def stop_project(sid):
    """Stop all nodes and unload the current project."""
    await project_manager.close_project()
    await sio.emit("project_stopped", {}, room=sid)
    await sio.emit("log", {"type": "info", "message": "Project stopped"})


@sio.event
async def delete_project(sid, data):
    """Delete a project."""
    project_id = data.get("id")
    if not project_id:
        return
    
    await project_manager.delete_project(project_id)
    await list_projects(sid)
    await sio.emit("log", {"type": "warning", "message": f"Project '{project_id}' deleted"})


# ==================== Agent Graph Operations ====================

@sio.event
async def get_agent_graph_state(sid):
    """Get the current agent graph state."""
    await sio.emit("agent_graph_state", _build_agent_graph_state(), room=sid)
    await sio.emit("agent_graph_agents", runtime.get_running_agents() if runtime else [], room=sid)


@sio.event
async def get_node_kg_data(sid, data):
    """Get knowledge graph data for a specific node."""
    node_id = data.get("node_id")
    if not node_id or not runtime._current_project_id:
        return
    
    kg = runtime.knowledge_graphs.get(node_id)
    if kg:
        kg_dict = kg.to_dict()
        entities = [
            {"name": name, "type": props.get("type", "Entity"), "properties": {k: v for k, v in props.items() if k != "type"}}
            for name, props in kg_dict.get("entities", {}).items()
        ]
        relationships = [
            {"from": r["entity1"], "to": r["entity2"], "type": r.get("relationship", ""), "properties": {k: v for k, v in r.items() if k not in ("entity1", "entity2", "relationship")}}
            for r in kg_dict.get("relationships", [])
        ]
        await sio.emit("node_kg_data", {"node_id": node_id, "entities": entities, "relationships": relationships}, room=sid)
    else:
        await sio.emit("node_kg_data", {"node_id": node_id, "entities": [], "relationships": []}, room=sid)


@sio.event
async def add_node(sid, data):
    """Add a node to the agent graph."""
    try:
        node_type = NodeType(data.get("type"))
        position = Position(
            x=data.get("x", 0),
            y=data.get("y", 0)
        )
        
        # Create config based on type
        config_data = data.get("config", {})
        if node_type == NodeType.AGENT:
            config = AgentNodeConfig(**config_data)
        elif node_type == NodeType.KNOWLEDGE_GRAPH:
            config = KnowledgeGraphNodeConfig(**config_data)
        elif node_type == NodeType.MEMORY_STREAM:
            config = MemoryStreamNodeConfig(**config_data)
        elif node_type == NodeType.TOOLBOX:
            config = ToolboxNodeConfig(**config_data)
        elif node_type == NodeType.TEXT_INPUT:
            config = TextInputNodeConfig(**config_data)
        elif node_type == NodeType.VOICE_INPUT:
            config = VoiceInputNodeConfig(**config_data)
        elif node_type == NodeType.TEXT_OUTPUT:
            config = TextOutputNodeConfig(**config_data)
        elif node_type == NodeType.SCHEDULED_EVENT:
            config = ScheduledEventNodeConfig(**config_data)
        elif node_type == NodeType.WAIT_AND_COMBINE:
            config = WaitAndCombineNodeConfig(**config_data)
        else:
            await sio.emit("error", {"message": f"Unknown node type: {node_type}"}, room=sid)
            return
        
        node = Node(
            type=node_type,
            position=position,
            config=config,
        )
        
        if not project_manager.current_project:
            await sio.emit("error", {"message": "No project loaded"}, room=sid)
            return
        
        if runtime.is_deployed:
            await sio.emit("error", {"message": "Cannot add nodes while deployed. Undeploy first."}, room=sid)
            return
        
        project_manager.current_project.agent_graph.add_node(node)
        await project_manager.save_project()
        await sio.emit("agent_graph_state", _build_agent_graph_state(), room=sid)
        await sio.emit("log", {"type": "success", "message": f"Node '{config_data.get('name', node_type.value)}' added"})
        
    except ValueError as e:
        await sio.emit("error", {"message": str(e)}, room=sid)
    except Exception as e:
        logger.error(f"Failed to add node: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def remove_node(sid, data):
    """Remove a node from the agent graph."""
    node_id = data.get("id")
    if not node_id:
        return
    
    if not project_manager.current_project:
        await sio.emit("error", {"message": "No project loaded"}, room=sid)
        return
    
    if runtime.is_deployed:
        await sio.emit("error", {"message": "Cannot remove nodes while deployed. Undeploy first."}, room=sid)
        return
    
    project_manager.current_project.agent_graph.remove_node(node_id)
    await project_manager.save_project()
    await sio.emit("agent_graph_state", _build_agent_graph_state(), room=sid)


@sio.event
async def update_node_position(sid, data):
    """Update a node's position."""
    node_id = data.get("id")
    x = data.get("x", 0)
    y = data.get("y", 0)
    
    if node_id and project_manager.current_project:
        node = project_manager.current_project.agent_graph.get_node(node_id)
        if node:
            node.position.x = x
            node.position.y = y
            # Don't save on every position update - let frontend batch these


@sio.event
async def update_node_config(sid, data):
    """Update a node's configuration."""
    node_id = data.get("id")
    config_updates = data.get("config", {})
    
    if node_id and config_updates and project_manager.current_project:
        node = project_manager.current_project.agent_graph.get_node(node_id)
        if node:
            for key, value in config_updates.items():
                if hasattr(node.config, key):
                    setattr(node.config, key, value)
            logger.info(f"Updated config for node {node_id}: {config_updates}")
        await project_manager.save_project()
        await sio.emit("agent_graph_state", _build_agent_graph_state(), room=sid)


@sio.event
async def add_edge(sid, data):
    """Add an edge between nodes."""
    try:
        if not project_manager.current_project:
            await sio.emit("error", {"message": "No project loaded"}, room=sid)
            return
        
        edge = Edge(
            source_node=data.get("source_node"),
            source_port=data.get("source_port"),
            target_node=data.get("target_node"),
            target_port=data.get("target_port"),
            edge_type=EdgeType(data.get("edge_type", "message")),
        )
        
        project_manager.current_project.agent_graph.add_edge(edge)
        await project_manager.save_project()
        await sio.emit("agent_graph_state", _build_agent_graph_state(), room=sid)
        
    except Exception as e:
        logger.error(f"Failed to add edge: {e}")
        await sio.emit("error", {"message": str(e)}, room=sid)


@sio.event
async def remove_edge(sid, data):
    """Remove an edge from the agent graph."""
    edge_id = data.get("id")
    if not edge_id:
        return
    
    if not project_manager.current_project:
        await sio.emit("error", {"message": "No project loaded"}, room=sid)
        return
    
    project_manager.current_project.agent_graph.remove_edge(edge_id)
    await project_manager.save_project()
    await sio.emit("agent_graph_state", _build_agent_graph_state(), room=sid)


@sio.event
async def agent_graph_send_user_message(sid, data):
    """Send a user message through the agent graph."""
    global tts_instance
    
    user = data.get("user", "User")
    content = data.get("message", "")
    
    # Echo the user's message
    await sio.emit("chat_message", {
        "user": user,
        "message": content,
        "source": "agent_graph"
    }, room=sid)
    
    responses = await runtime.send_user_message(content, user)
    
    for resp in responses:
        logger.debug(f"Agent graph response from {resp['agent_name']}: {resp['response'][:50]}...")
        
        # Check this client's TTS preference
        prefs = _client_preferences.get(sid, {})
        if prefs.get("tts_enabled") and tts_instance is not None:
            try:
                audio_bytes = tts_instance.synthesize(resp["response"])
                if audio_bytes:
                    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                    await sio.emit("tts_audio", {
                        "audioUrl": f"data:audio/wav;base64,{audio_b64}"
                    }, room=sid)
                    logger.info(f"Generated TTS audio for client {sid}: {len(audio_bytes)} bytes")
            except Exception as e:
                logger.error(f"TTS synthesis failed: {e}")


# ==================== TTS ====================

@sio.event
async def get_tts_settings(sid):
    """Get current TTS settings."""
    global tts_enabled, tts_instance
    
    settings = {
        "enabled": tts_enabled,
        "available": PIPER_AVAILABLE,
        "voice": None,
        "speed": 1.0,
        "speaker": 0,
    }
    
    if tts_instance is not None:
        instance_settings = tts_instance.get_settings()
        settings.update({
            "voice": instance_settings.get("voice"),
            "speed": instance_settings.get("speed", 1.0),
            "speaker": instance_settings.get("speaker", 0),
        })
    
    await sio.emit("tts_settings", settings, room=sid)


@sio.event
async def set_tts_enabled(sid, data):
    """Set per-client TTS preference."""
    global tts_instance
    enabled = data.get("enabled", False)
    
    if sid not in _client_preferences:
        _client_preferences[sid] = {}
    _client_preferences[sid]["tts_enabled"] = enabled
    
    # Initialize TTS instance if enabling and not yet created
    if enabled and tts_instance is None:
        tts_instance = get_tts()
        logger.info("TTS instance initialized on first client enable")
    
    logger.info(f"Client {sid} TTS preference: {enabled}")
    await sio.emit("tts_preference_updated", {"enabled": enabled}, room=sid)


@sio.event
async def set_tts_settings(sid, data):
    """Update TTS settings."""
    global tts_enabled, tts_instance
    
    if not PIPER_AVAILABLE:
        await sio.emit("error", {"message": "Piper TTS is not available. Install with: pip install piper-tts"}, room=sid)
        return
    
    # Update enabled state
    if "enabled" in data:
        tts_enabled = data["enabled"]
        logger.info(f"TTS {'enabled' if tts_enabled else 'disabled'}")
        
        # Also set this client's per-client TTS preference
        if sid not in _client_preferences:
            _client_preferences[sid] = {}
        _client_preferences[sid]["tts_enabled"] = data["enabled"]
        
        # Initialize TTS instance if enabling and not yet created
        if tts_enabled and tts_instance is None:
            tts_instance = get_tts()
    
    # Update voice
    if "voice" in data and tts_instance is not None:
        voice = data["voice"]
        if tts_instance.set_voice(voice):
            logger.info(f"TTS voice set to: {voice}")
        else:
            await sio.emit("error", {"message": f"Failed to load voice: {voice}"}, room=sid)
    
    # Update speed
    if "speed" in data and tts_instance is not None:
        tts_instance.set_speed(data["speed"])
        logger.info(f"TTS speed set to: {data['speed']}")
    
    # Update speaker
    if "speaker" in data and tts_instance is not None:
        tts_instance.set_speaker(data["speaker"])
        logger.info(f"TTS speaker set to: {data['speaker']}")
    
    # Emit updated settings
    await get_tts_settings(sid)


@sio.event
async def get_tts_voices(sid):
    """Get list of available TTS voices."""
    global tts_instance
    
    if not PIPER_AVAILABLE:
        await sio.emit("tts_voices", {"voices": [], "error": "Piper TTS not available"}, room=sid)
        return
    
    # Initialize instance if needed
    if tts_instance is None:
        tts_instance = get_tts()
    
    voices = tts_instance.list_voices()
    await sio.emit("tts_voices", {
        "voices": [
            {
                "key": v.key,
                "name": v.name,
                "language": v.language,
                "quality": v.quality,
                "downloaded": v.downloaded,
                "num_speakers": v.num_speakers,
                "speaker_id_map": v.speaker_id_map,
            }
            for v in voices
        ]
    }, room=sid)


@sio.event
async def download_tts_voice(sid, data):
    """Download a TTS voice model."""
    global tts_instance, tts_enabled
    
    if not PIPER_AVAILABLE:
        await sio.emit("error", {"message": "Piper TTS not available"}, room=sid)
        return
    
    voice_key = data.get("voice")
    if not voice_key:
        await sio.emit("error", {"message": "Voice key required"}, room=sid)
        return
    
    if tts_instance is None:
        tts_instance = get_tts()
    
    try:
        await sio.emit("tts_download_progress", {"voice": voice_key, "status": "downloading"})
        success = tts_instance.download_voice(voice_key)
        
        if success:
            await sio.emit("tts_download_progress", {"voice": voice_key, "status": "complete"})
            await sio.emit("log", {"type": "success", "message": f"Voice '{voice_key}' downloaded"})
            
            # Auto-select the downloaded voice
            if tts_instance.set_voice(voice_key):
                logger.info(f"Auto-selected voice: {voice_key}")
            
            # Refresh voice list
            await get_tts_voices(sid)
            
            # Emit updated TTS settings with the new voice
            await sio.emit("tts_settings", {
                "enabled": tts_enabled,
                "available": PIPER_AVAILABLE,
                "voice": tts_instance.current_voice_name,
                "speed": tts_instance.speed,
                "speaker": tts_instance.speaker,
            })
        else:
            await sio.emit("tts_download_progress", {"voice": voice_key, "status": "failed"})
            await sio.emit("error", {"message": f"Failed to download voice '{voice_key}'"}, room=sid)
    except Exception as e:
        logger.error(f"Voice download failed: {e}")
        await sio.emit("tts_download_progress", {"voice": voice_key, "status": "failed"})
        await sio.emit("error", {"message": str(e)}, room=sid)


# ==================== STT Settings ====================

@sio.event
async def get_stt_settings(sid):
    """Get current STT settings from project (project-level config, NOT per-client enabled state)."""
    # Note: "enabled" is per-client, not included here
    settings = {
        "device_id": None,
        "device_label": None,
        "wake_words": ["hey beezle", "ok beezle"],
        "stop_words": ["stop listening", "goodbye", "that's all"],
        "max_duration": 30.0,
    }
    
    if project_manager.current_project:
        stt = project_manager.current_project.stt_settings
        settings = {
            "device_id": stt.device_id,
            "device_label": stt.device_label,
            "wake_words": stt.wake_words,
            "stop_words": stt.stop_words,
            "max_duration": stt.max_duration,
        }
    
    await sio.emit("stt_settings", settings, room=sid)


@sio.event
async def set_stt_enabled(sid, data):
    """Set per-client STT preference."""
    enabled = data.get("enabled", False)
    
    if sid not in _client_preferences:
        _client_preferences[sid] = {}
    _client_preferences[sid]["stt_enabled"] = enabled
    
    # Emit back to client so Chat component can react
    await sio.emit("stt_enabled_changed", {"enabled": enabled}, room=sid)
    
    logger.info(f"Client {sid} STT preference: {enabled}")


@sio.event
async def set_skip_wake_word(sid, data):
    """Echo skip wake word setting back to client for Chat component."""
    enabled = data.get("enabled", False)
    await sio.emit("skip_wake_word_changed", {"enabled": enabled}, room=sid)
    logger.debug(f"Client {sid} skip_wake_word: {enabled}")


@sio.event
async def set_stt_settings(sid, data):
    """Update STT settings (project-level config, NOT per-client enabled state)."""
    if not project_manager.current_project:
        await sio.emit("error", {"message": "No project loaded"}, room=sid)
        return
    
    stt = project_manager.current_project.stt_settings
    
    # Note: "enabled" is now per-client, handled by set_stt_enabled
    # This handler only manages project-level config (device, wake words, etc.)
    
    if "device_id" in data:
        stt.device_id = data["device_id"]
    
    if "device_label" in data:
        stt.device_label = data["device_label"]
    
    if "wake_words" in data:
        stt.wake_words = data["wake_words"]
    
    if "stop_words" in data:
        stt.stop_words = data["stop_words"]
    
    if "max_duration" in data:
        stt.max_duration = float(data["max_duration"])
    
    # Broadcast updated settings to ALL connected clients
    # Note: "enabled" is excluded - it's per-client
    settings = {
        "device_id": stt.device_id,
        "device_label": stt.device_label,
        "wake_words": stt.wake_words,
        "stop_words": stt.stop_words,
        "max_duration": stt.max_duration,
    }
    await sio.emit("stt_settings", settings)  # Broadcast to all
    logger.info(f"STT settings updated")


# ==================== STT Streaming ====================

# Per-client audio buffers for streaming STT
_stt_audio_buffers: dict[str, dict] = {}

@sio.event
async def stt_stream_start(sid, data):
    """Start a new STT streaming session."""
    skip_wake_word = data.get("skip_wake_word", False)
    
    # Initialize audio buffer for this client
    _stt_audio_buffers[sid] = {
        "chunks": [],
        "skip_wake_word": skip_wake_word,
        "active": skip_wake_word,  # If skipping wake word, start active immediately
    }
    
    if skip_wake_word:
        await sio.emit("stt_activated", room=sid)
    
    logger.info(f"STT stream started for {sid} (skip_wake_word={skip_wake_word})")


@sio.event
async def stt_stream_chunk(sid, data):
    """Receive an audio chunk for STT processing."""
    import base64
    
    # Auto-create session if it doesn't exist (handles race conditions)
    if sid not in _stt_audio_buffers:
        _stt_audio_buffers[sid] = {
            "chunks": [],
            "skip_wake_word": False,
            "active": False,
        }
    
    buffer = _stt_audio_buffers[sid]
    audio_b64 = data.get("audio", "")
    speech_detected = data.get("speech", True)
    
    if audio_b64:
        try:
            audio_bytes = base64.b64decode(audio_b64)
            buffer["chunks"].append(audio_bytes)
        except Exception as e:
            logger.error(f"Failed to decode audio chunk: {e}")
    
    # Update state based on speech detection
    if speech_detected and not buffer["active"]:
        buffer["active"] = True
        await sio.emit("stt_activated", room=sid)
    elif not speech_detected and buffer["active"]:
        # Speech ended - transcribe what we have
        if buffer["chunks"]:
            await _transcribe_and_send(sid, buffer)


@sio.event
async def stt_stream_stop(sid):
    """Stop STT streaming and transcribe any remaining audio."""
    if sid in _stt_audio_buffers:
        buffer = _stt_audio_buffers[sid]
        
        # Transcribe any remaining audio
        if buffer["chunks"]:
            await _transcribe_and_send(sid, buffer)
        
        del _stt_audio_buffers[sid]
    
    await sio.emit("stt_deactivated", room=sid)
    logger.debug(f"STT stream stopped for {sid}")


async def _transcribe_and_send(sid: str, buffer: dict):
    """Transcribe accumulated audio and send the result."""
    from beezle_bug.voice.transcriber import get_transcriber
    import struct
    
    if not buffer["chunks"]:
        return
    
    try:
        # Combine all chunks into one audio buffer
        all_audio = b"".join(buffer["chunks"])
        
        # Create WAV header for the raw PCM data
        # The frontend sends 16-bit mono PCM at 16000 Hz
        sample_rate = 16000
        num_channels = 1
        bits_per_sample = 16
        num_samples = len(all_audio) // 2
        
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + len(all_audio),
            b'WAVE',
            b'fmt ',
            16,  # PCM format chunk size
            1,   # Audio format (PCM)
            num_channels,
            sample_rate,
            sample_rate * num_channels * bits_per_sample // 8,  # Byte rate
            num_channels * bits_per_sample // 8,  # Block align
            bits_per_sample,
            b'data',
            len(all_audio)
        )
        
        wav_data = wav_header + all_audio
        
        # Get transcriber and transcribe
        transcriber = get_transcriber()
        text = transcriber.transcribe(wav_data)
        
        if text and text.strip():
            logger.info(f"Transcribed for {sid}: '{text}' - emitting stt_final_text")
            await sio.emit("stt_final_text", {"text": text}, room=sid)
            logger.debug(f"stt_final_text emitted to {sid}")
        
        # Clear the buffer
        buffer["chunks"] = []
        buffer["active"] = False
        
    except Exception as e:
        logger.error(f"Transcription failed for {sid}: {e}")
        buffer["chunks"] = []
        buffer["active"] = False


# ==================== General Settings ====================

@sio.event
async def get_general_settings(sid):
    """Get current general settings."""
    settings = {
        "storage_backend": DB_BACKEND,
    }
    await sio.emit("general_settings", settings, room=sid)


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("Beezle Bug WebChat Server")
    print("=" * 50)
    print(f"Data directory: {DATA_DIR}")
    print("Open http://localhost:5000 in your browser")
    print("Or use the React UI at http://localhost:5173")
    print("=" * 50)
    
    uvicorn.run(socket_app, host="0.0.0.0", port=5000)
