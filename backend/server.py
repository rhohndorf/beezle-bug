"""
WebSocket server for Beezle Bug.

Handles:
- Agent lifecycle management via AgentManager
- Chat messages
- Scheduler for autonomous agent behavior
- Event forwarding for introspection
"""

# Monkey-patch must be first for eventlet to work with threads
import eventlet
eventlet.monkey_patch()

import os
from loguru import logger
from pathlib import Path
from flask import Flask, render_template, send_from_directory, abort
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from beezle_bug import constants as const
from beezle_bug.events import EventBus
from beezle_bug.scheduler import Scheduler
from beezle_bug.template import TemplateLoader
from beezle_bug.tools.toolbox_factory import ToolboxFactory
from beezle_bug.storage import StorageService
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
    UserInputNodeConfig,
    UserOutputNodeConfig,
    ScheduledEventNodeConfig,
    TTSSettings,
)
from beezle_bug.voice.tts import PiperTTS, get_tts, PIPER_AVAILABLE

import base64

app = Flask(__name__)
app.config["SECRET_KEY"] = "beezle-secret"
CORS(app)
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

# Data directory for persistence
DATA_DIR = Path(os.environ.get("BEEZLE_DATA_DIR", const.DEFAULT_DATA_DIR))

# Global components
event_bus = EventBus()
scheduler = Scheduler(tick_interval=1.0)
toolbox_factory = ToolboxFactory()
template_loader = TemplateLoader(DATA_DIR)

# TTS State
tts_enabled = False
tts_instance: PiperTTS = None
AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)



def event_handler(event):
    """Forward agent events to connected clients."""
    try:
        socketio.emit('agent_event', event.to_dict())
    except Exception as e:
        logger.error(f"Failed to emit event: {e}")



# Initialize Storage, Runtime, and ProjectManager
def on_agent_graph_message(agent_id: str, agent_name: str, message: str):
    """Callback for agent graph messages - emits to all connected clients."""
    global tts_enabled, tts_instance
    
    msg_data = {
        "agentId": agent_id,
        "user": agent_name,
        "message": message,
        "source": "agent_graph"
    }
    
    # Generate TTS audio if enabled
    if tts_enabled and tts_instance is not None:
        try:
            if tts_instance.voice is None:
                logger.warning("TTS enabled but no voice loaded")
            else:
                audio_bytes = tts_instance.synthesize(message)
                if audio_bytes:
                    # Send as base64 data URL - no disk write needed
                    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                    msg_data["audioUrl"] = f"data:audio/wav;base64,{audio_b64}"
                    logger.info(f"Generated TTS audio: {len(audio_bytes)} bytes")
                else:
                    logger.warning("TTS synthesis returned no audio")
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
    
    socketio.emit("chat_message", msg_data)


storage = StorageService(data_dir=DATA_DIR)

runtime = AgentGraphRuntime(
    storage=storage,
    event_bus=event_bus,
    scheduler=scheduler,
    template_loader=template_loader,
    toolbox_factory=toolbox_factory,
    on_agent_graph_message=on_agent_graph_message,
)

project_manager = ProjectManager(storage=storage, runtime=runtime)

# Subscribe to all events
event_bus.subscribe_all(event_handler)

# Start scheduler
scheduler.start()


# ==================== Helper Functions ====================

def get_agent_graph_state() -> dict:
    """Get the current agent graph state for the frontend."""
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


# ==================== Routes ====================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/audio/<filename>")
def serve_audio(filename):
    """Serve generated TTS audio files."""
    audio_path = AUDIO_DIR / filename
    if not audio_path.exists():
        abort(404)
    return send_from_directory(AUDIO_DIR, filename, mimetype="audio/wav")


# ==================== WebSocket Handlers ====================

@socketio.on("connect")
def handle_connect():
    logger.info("Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    logger.info("Client disconnected")


# ==================== Tools & Templates ====================

@socketio.on("get_tools")
def handle_get_tools():
    """Get all available tools and presets."""
    emit("tools_list", {
        "tools": toolbox_factory.list_tools(),
        "presets": {
            name: toolbox_factory.get_preset(name) 
            for name in toolbox_factory.list_presets()
        }
    })


@socketio.on("get_templates")
def handle_get_templates():
    """Get all available system message templates."""
    emit("templates_list", {
        "templates": template_loader.list_templates()
    })


@socketio.on("get_template_content")
def handle_get_template_content(data):
    """Get the raw content of a specific template."""
    name = data.get("name")
    if not name:
        emit("error", {"message": "Template name required"})
        return
    
    try:
        content = template_loader.get_content(name)
        emit("template_content", {
            "name": name,
            "content": content
        })
    except FileNotFoundError as e:
        emit("error", {"message": str(e)})


@socketio.on("save_template")
def handle_save_template(data):
    """Create or update a template file."""
    name = data.get("name")
    content = data.get("content")
    
    if not name:
        emit("error", {"message": "Template name required"})
        return
    if content is None:
        emit("error", {"message": "Template content required"})
        return
    
    try:
        template_loader.save(name, content)
        emit("template_saved", {"name": name})
        socketio.emit("log", {"type": "success", "message": f"Template saved: {name}"})
        # Also emit updated template list
        emit("templates_list", {"templates": template_loader.list_templates()})
    except Exception as e:
        logger.error(f"Failed to save template: {e}")
        emit("error", {"message": f"Failed to save template: {e}"})


@socketio.on("delete_template")
def handle_delete_template(data):
    """Delete a template file."""
    name = data.get("name")
    if not name:
        emit("error", {"message": "Template name required"})
        return
    
    try:
        template_loader.delete(name)
        emit("template_deleted", {"name": name})
        socketio.emit("log", {"type": "success", "message": f"Template deleted: {name}"})
        # Also emit updated template list
        emit("templates_list", {"templates": template_loader.list_templates()})
    except FileNotFoundError as e:
        emit("error", {"message": str(e)})
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        emit("error", {"message": f"Failed to delete template: {e}"})

# ==================== Chat ====================

@socketio.on("send_message")
def handle_message(data):
    """Handle chat messages from users."""
    logger.info(f"Message: {data}")
    emit("chat_message", data, broadcast=True)
    
    user = data.get("user", "User")
    message = data.get("message", "")
    target_agent_id = data.get("agentId")
    
    # If an agent graph project is active, route through it
    if project_manager.current_project and runtime.agents:
        def process_agent_graph():
            responses = runtime.send_user_message(message, user)
            for resp in responses:
                logger.debug(f"Agent graph response from {resp['agent_name']}")
        
        socketio.start_background_task(process_agent_graph)
        return


# ==================== Schedule ====================

@socketio.on("get_schedule")
def handle_get_schedule():
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
    emit("schedule_update", {"tasks": tasks})


@socketio.on("pause_schedule_task")
def handle_pause_task(data):
    """Pause a scheduled task."""
    task_id = data.get("taskId")
    if task_id:
        scheduler.pause_task(task_id)
        handle_get_schedule()


@socketio.on("resume_schedule_task")
def handle_resume_task(data):
    """Resume a paused task."""
    task_id = data.get("taskId")
    if task_id:
        scheduler.resume_task(task_id)
        handle_get_schedule()


@socketio.on("cancel_schedule_task")
def handle_cancel_task(data):
    """Cancel a scheduled task."""
    task_id = data.get("taskId")
    if task_id:
        scheduler.cancel_task(task_id)
        handle_get_schedule()

# ==================== Project Management ====================

@socketio.on("list_projects")
def handle_list_projects():
    """List all saved projects."""
    projects = project_manager.list_projects()
    emit("projects_list", {"projects": projects})


@socketio.on("create_project")
def handle_create_project(data):
    """Create a new project."""
    name = data.get("name", "Untitled Project")
    try:
        project = project_manager.create_project(name)
        emit("project_created", {
            "id": project.id,
            "name": project.name,
        })
        handle_list_projects()
        socketio.emit("log", {"type": "success", "message": f"Project '{name}' created"})
    except Exception as e:
        logger.error(f"Failed to create project: {e}")
        emit("error", {"message": str(e)})


@socketio.on("load_project")
def handle_load_project(data):
    """Load a project and instantiate its agent graph."""
    global tts_enabled, tts_instance
    
    project_id = data.get("id")
    if not project_id:
        return
    
    try:
        project = project_manager.load_project(project_id)
        
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
        
        emit("project_loaded", {
            "id": project.id,
            "name": project.name,
            "tts_settings": {
                "enabled": tts_settings.enabled,
                "voice": tts_settings.voice,
                "speed": tts_settings.speed,
                "speaker": tts_settings.speaker,
            }
        })
        emit("agent_graph_state", get_agent_graph_state())
        # Also emit current TTS settings so UI updates
        handle_get_tts_settings()
        socketio.emit("log", {"type": "success", "message": f"Project '{project.name}' loaded"})
    except FileNotFoundError:
        emit("error", {"message": f"Project {project_id} not found"})
    except Exception as e:
        logger.error(f"Failed to load project: {e}")
        emit("error", {"message": str(e)})


@socketio.on("save_project")
def handle_save_project():
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
        
        project_manager.save_project()
        socketio.emit("log", {"type": "success", "message": "Project saved"})
    except ValueError as e:
        emit("error", {"message": str(e)})


@socketio.on("deploy_project")
def handle_deploy_project():
    """Deploy the current project - instantiate all agents and resources."""
    try:
        if not project_manager.current_project:
            emit("error", {"message": "No project loaded"})
            return
        
        runtime.deploy(
            project_manager.current_project.agent_graph,
            project_manager.current_project.id
        )
        socketio.emit("agent_graph_state", get_agent_graph_state())
        # Emit agent graph agents list so Agents tab can display them
        socketio.emit("agent_graph_agents", runtime.get_running_agents())
        socketio.emit("log", {"type": "success", "message": f"Project deployed: {project_manager.current_project.name}"})
    except Exception as e:
        import traceback
        logger.error(f"Failed to deploy project: {e}\n{traceback.format_exc()}")
        emit("error", {"message": str(e) or "Unknown error during deployment"})


@socketio.on("undeploy_project")
def handle_undeploy_project():
    """Undeploy the current project - stop all agents and resources."""
    try:
        runtime.undeploy()
        socketio.emit("agent_graph_state", get_agent_graph_state())
        # Clear agent graph agents
        socketio.emit("agent_graph_agents", [])
        socketio.emit("log", {"type": "success", "message": "Project undeployed"})
    except Exception as e:
        logger.error(f"Failed to undeploy project: {e}")
        emit("error", {"message": str(e)})


@socketio.on("stop_project")
def handle_stop_project():
    """Stop all nodes and unload the current project."""
    project_manager.close_project()
    emit("project_stopped", {})
    socketio.emit("log", {"type": "info", "message": "Project stopped"})


@socketio.on("delete_project")
def handle_delete_project(data):
    """Delete a project."""
    project_id = data.get("id")
    if not project_id:
        return
    
    project_manager.delete_project(project_id)
    handle_list_projects()
    socketio.emit("log", {"type": "warning", "message": f"Project '{project_id}' deleted"})


# ==================== Agent Graph Operations ====================

@socketio.on("get_agent_graph_state")
def handle_get_agent_graph_state():
    """Get the current agent graph state."""
    emit("agent_graph_state", get_agent_graph_state())
    # Also emit agent graph agents so Agents tab displays them
    emit("agent_graph_agents", runtime.get_running_agents())


@socketio.on("add_node")
def handle_add_node(data):
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
        elif node_type == NodeType.USER_INPUT:
            config = UserInputNodeConfig(**config_data)
        elif node_type == NodeType.USER_OUTPUT:
            config = UserOutputNodeConfig(**config_data)
        elif node_type == NodeType.SCHEDULED_EVENT:
            config = ScheduledEventNodeConfig(**config_data)
        else:
            emit("error", {"message": f"Unknown node type: {node_type}"})
            return
        
        node = Node(
            type=node_type,
            position=position,
            config=config,
        )
        
        if not project_manager.current_project:
            emit("error", {"message": "No project loaded"})
            return
        
        if runtime.is_deployed:
            emit("error", {"message": "Cannot add nodes while deployed. Undeploy first."})
            return
        
        project_manager.current_project.agent_graph.add_node(node)
        project_manager.save_project()
        emit("agent_graph_state", get_agent_graph_state())
        socketio.emit("log", {"type": "success", "message": f"Node '{config_data.get('name', node_type.value)}' added"})
        
    except ValueError as e:
        emit("error", {"message": str(e)})
    except Exception as e:
        logger.error(f"Failed to add node: {e}")
        emit("error", {"message": str(e)})


@socketio.on("remove_node")
def handle_remove_node(data):
    """Remove a node from the agent graph."""
    node_id = data.get("id")
    if not node_id:
        return
    
    if not project_manager.current_project:
        emit("error", {"message": "No project loaded"})
        return
    
    if runtime.is_deployed:
        emit("error", {"message": "Cannot remove nodes while deployed. Undeploy first."})
        return
    
    project_manager.current_project.agent_graph.remove_node(node_id)
    project_manager.save_project()
    emit("agent_graph_state", get_agent_graph_state())


@socketio.on("update_node_position")
def handle_update_node_position(data):
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


@socketio.on("update_node_config")
def handle_update_node_config(data):
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
        project_manager.save_project()
        emit("agent_graph_state", get_agent_graph_state())


@socketio.on("add_edge")
def handle_add_edge(data):
    """Add an edge between nodes."""
    try:
        if not project_manager.current_project:
            emit("error", {"message": "No project loaded"})
            return
        
        edge = Edge(
            source_node=data.get("source_node"),
            source_port=data.get("source_port"),
            target_node=data.get("target_node"),
            target_port=data.get("target_port"),
            edge_type=EdgeType(data.get("edge_type", "message")),
        )
        
        project_manager.current_project.agent_graph.add_edge(edge)
        project_manager.save_project()
        emit("agent_graph_state", get_agent_graph_state())
        
    except Exception as e:
        logger.error(f"Failed to add edge: {e}")
        emit("error", {"message": str(e)})


@socketio.on("remove_edge")
def handle_remove_edge(data):
    """Remove an edge from the agent graph."""
    edge_id = data.get("id")
    if not edge_id:
        return
    
    if not project_manager.current_project:
        emit("error", {"message": "No project loaded"})
        return
    
    project_manager.current_project.agent_graph.remove_edge(edge_id)
    project_manager.save_project()
    emit("agent_graph_state", get_agent_graph_state())


@socketio.on("agent_graph_send_user_message")
def handle_agent_graph_user_message(data):
    """Send a user message through the agent graph."""
    user = data.get("user", "User")
    content = data.get("message", "")
    
    # Echo the user's message
    emit("chat_message", {
        "user": user,
        "message": content,
        "source": "agent_graph"
    }, broadcast=True)
    
    def process():
        responses = runtime.send_user_message(content, user)
        # Responses are already emitted via on_agent_graph_message callback
        # but we can log them here
        for resp in responses:
            logger.debug(f"Agent graph response from {resp['agent_name']}: {resp['response'][:50]}...")
    
    socketio.start_background_task(process)


# ==================== TTS ====================

@socketio.on("get_tts_settings")
def handle_get_tts_settings():
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
    
    emit("tts_settings", settings)


@socketio.on("set_tts_settings")
def handle_set_tts_settings(data):
    """Update TTS settings."""
    global tts_enabled, tts_instance
    
    if not PIPER_AVAILABLE:
        emit("error", {"message": "Piper TTS is not available. Install with: pip install piper-tts"})
        return
    
    # Update enabled state
    if "enabled" in data:
        tts_enabled = data["enabled"]
        logger.info(f"TTS {'enabled' if tts_enabled else 'disabled'}")
        
        # Initialize TTS instance if enabling and not yet created
        if tts_enabled and tts_instance is None:
            tts_instance = get_tts()
    
    # Update voice
    if "voice" in data and tts_instance is not None:
        voice = data["voice"]
        if tts_instance.set_voice(voice):
            logger.info(f"TTS voice set to: {voice}")
        else:
            emit("error", {"message": f"Failed to load voice: {voice}"})
    
    # Update speed
    if "speed" in data and tts_instance is not None:
        tts_instance.set_speed(data["speed"])
        logger.info(f"TTS speed set to: {data['speed']}")
    
    # Update speaker
    if "speaker" in data and tts_instance is not None:
        tts_instance.set_speaker(data["speaker"])
        logger.info(f"TTS speaker set to: {data['speaker']}")
    
    # Emit updated settings
    handle_get_tts_settings()


@socketio.on("get_tts_voices")
def handle_get_tts_voices():
    """Get list of available TTS voices."""
    global tts_instance
    
    if not PIPER_AVAILABLE:
        emit("tts_voices", {"voices": [], "error": "Piper TTS not available"})
        return
    
    # Initialize instance if needed
    if tts_instance is None:
        tts_instance = get_tts()
    
    voices = tts_instance.list_voices()
    emit("tts_voices", {
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
    })


@socketio.on("download_tts_voice")
def handle_download_tts_voice(data):
    """Download a TTS voice model."""
    global tts_instance
    
    if not PIPER_AVAILABLE:
        emit("error", {"message": "Piper TTS not available"})
        return
    
    voice_key = data.get("voice")
    if not voice_key:
        emit("error", {"message": "Voice key required"})
        return
    
    if tts_instance is None:
        tts_instance = get_tts()
    
    def do_download():
        global tts_enabled
        try:
            socketio.emit("tts_download_progress", {"voice": voice_key, "status": "downloading"})
            success = tts_instance.download_voice(voice_key)
            
            if success:
                socketio.emit("tts_download_progress", {"voice": voice_key, "status": "complete"})
                socketio.emit("log", {"type": "success", "message": f"Voice '{voice_key}' downloaded"})
                
                # Auto-select the downloaded voice
                if tts_instance.set_voice(voice_key):
                    logger.info(f"Auto-selected voice: {voice_key}")
                
                # Refresh voice list
                voices = tts_instance.list_voices()
                socketio.emit("tts_voices", {
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
                })
                
                # Also emit updated TTS settings with the new voice
                socketio.emit("tts_settings", {
                    "enabled": tts_enabled,
                    "available": PIPER_AVAILABLE,
                    "voice": tts_instance.current_voice_name,
                    "speed": tts_instance.speed,
                    "speaker": tts_instance.speaker,
                })
            else:
                socketio.emit("tts_download_progress", {"voice": voice_key, "status": "failed"})
                socketio.emit("error", {"message": f"Failed to download voice '{voice_key}'"})
        except Exception as e:
            logger.error(f"Voice download failed: {e}")
            socketio.emit("tts_download_progress", {"voice": voice_key, "status": "failed"})
            socketio.emit("error", {"message": str(e)})
    
    socketio.start_background_task(do_download)


# ==================== Voice / STT ====================

# Lazy-loaded voice components
_transcriber = None
_audio_buffers = {}  # sid -> AudioBuffer

def get_transcriber():
    """Get or create the transcriber singleton."""
    global _transcriber
    if _transcriber is None:
        from beezle_bug.voice import Transcriber
        _transcriber = Transcriber(model_size="base", device="cuda", compute_type="float16")
    return _transcriber


@socketio.on("audio_start")
def handle_audio_start(data=None):
    """Start a new audio recording session."""
    from beezle_bug.voice.vad import AudioBuffer
    from flask import request
    
    sid = request.sid
    _audio_buffers[sid] = AudioBuffer(max_duration_seconds=30.0, sample_rate=16000)
    logger.debug(f"Audio recording started for session {sid}")
    emit("audio_status", {"status": "recording"})


@socketio.on("audio_chunk")
def handle_audio_chunk(data):
    """Receive audio chunk from browser."""
    from flask import request
    
    sid = request.sid
    if sid not in _audio_buffers:
        logger.warning(f"Received audio chunk for unknown session {sid}")
        return
    
    # data should be bytes or base64
    if isinstance(data, dict) and "audio" in data:
        import base64
        audio_bytes = base64.b64decode(data["audio"])
    elif isinstance(data, bytes):
        audio_bytes = data
    else:
        logger.warning(f"Invalid audio chunk format: {type(data)}")
        return
    
    _audio_buffers[sid].append(audio_bytes)


@socketio.on("audio_end")
def handle_audio_end(data=None):
    """End audio recording and transcribe."""
    from flask import request
    
    sid = request.sid
    if sid not in _audio_buffers:
        logger.warning(f"No audio buffer for session {sid}")
        emit("transcription", {"error": "No audio recorded"})
        return
    
    buffer = _audio_buffers.pop(sid)
    audio_bytes = buffer.get_audio()
    
    if len(audio_bytes) < 1000:  # Too short
        logger.debug("Audio too short, skipping transcription")
        emit("transcription", {"text": "", "error": "Audio too short"})
        return
    
    def do_transcribe():
        try:
            # Add WAV header if raw PCM
            audio_with_header = _add_wav_header(audio_bytes, sample_rate=16000, channels=1)
            
            transcriber = get_transcriber()
            text = transcriber.transcribe(audio_with_header)
            
            logger.info(f"Transcribed: {text[:50]}...")
            socketio.emit("transcription", {"text": text}, to=sid)
            
            # Optionally auto-send to chat
            auto_send = data.get("auto_send", False) if isinstance(data, dict) else False
            if auto_send and text.strip():
                # Emit as user message
                socketio.emit("chat_message", {
                    "user": "User",
                    "message": text,
                    "source": "voice"
                }, broadcast=True)
                
                # Process with agent graph or agents
                if project_manager.current_project and runtime.agents:
                    responses = runtime.send_user_message(text, "User")
                    for resp in responses:
                        logger.debug(f"Voice response from {resp['agent_name']}")
                        
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            socketio.emit("transcription", {"error": str(e)}, to=sid)
    
    socketio.start_background_task(do_transcribe)


def _add_wav_header(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, bits_per_sample: int = 16) -> bytes:
    """Add WAV header to raw PCM data."""
    import struct
    
    data_size = len(pcm_data)
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,  # Subchunk1Size for PCM
        1,   # AudioFormat (PCM)
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b'data',
        data_size
    )
    
    return header + pcm_data


# ==================== Main ====================

if __name__ == "__main__":
    print("=" * 50)
    print("Beezle Bug WebChat Server")
    print("=" * 50)
    print(f"Data directory: {DATA_DIR}")
    print("Open http://localhost:5000 in your browser")
    print("Or use the React UI at http://localhost:5173")
    print("=" * 50)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
