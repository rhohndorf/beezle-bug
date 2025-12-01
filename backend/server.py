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
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from beezle_bug import constants as const
from beezle_bug.agents import AgentConfig
from beezle_bug.agents.agent_manager import AgentManager, AgentState
from beezle_bug.events import EventBus
from beezle_bug.exceptions import (
    AgentNotFoundError,
    AgentAlreadyInstancedError,
    AgentNotInstancedError
)
from beezle_bug.scheduler import Scheduler
from beezle_bug.template import TemplateLoader
from beezle_bug.tools.toolbox_factory import ToolboxFactory

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


def on_agent_message(agent_id: str, agent_name: str, message: str):
    """Callback for agent messages - emits to all connected clients."""
    socketio.emit("chat_message", {
        "agentId": agent_id,
        "user": agent_name,
        "message": message
    })


def event_handler(event):
    """Forward agent events to connected clients."""
    try:
        socketio.emit('agent_event', event.to_dict())
    except Exception as e:
        logger.error(f"Failed to emit event: {e}")


# Initialize AgentManager
agent_manager = AgentManager(
    data_dir=DATA_DIR,
    event_bus=event_bus,
    scheduler=scheduler,
    toolbox_factory=toolbox_factory,
    template_loader=template_loader,
    on_agent_message=on_agent_message
)

# Subscribe to all events
event_bus.subscribe_all(event_handler)

# Start scheduler
scheduler.start()


# ==================== Helper Functions ====================

def emit_agents_list():
    """Emit the combined list of persisted and instanced agents."""
    persisted = agent_manager.list_persisted_agents()
    instanced = agent_manager.list_instanced_agents()
    
    socketio.emit("agents_list", {
        "persisted": persisted,
        "instanced": instanced
    })


def emit_agent_status(agent_id: str):
    """Emit status for a specific agent."""
    agent = agent_manager.get_agent(agent_id)
    state = agent_manager.get_state(agent_id)
    
    if agent and state:
        socketio.emit("agent_status", {
            "id": agent_id,
            "name": agent.name,
            "state": state.value,
            "autonomousEnabled": agent_manager._is_autonomous_enabled(agent_id)
        })


def emit_knowledge_graph_state(agent_id: str):
    """Emit the full knowledge graph state for an agent."""
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        return
    
    kg = agent.knowledge_graph
    
    # Build entities list
    entities = []
    for entity_name in kg.graph.nodes():
        node_data = kg.graph.nodes[entity_name]
        entities.append({
            "name": entity_name,
            "type": node_data.get("type", "Entity"),
            "properties": {k: v for k, v in node_data.items() if k != "type"}
        })
    
    # Build relationships list
    relationships = []
    for entity1, entity2, edge_data in kg.graph.edges(data=True):
        rel_type = edge_data.get("relationship", "related_to")
        props = {k: v for k, v in edge_data.items() if k != "relationship"}
        relationships.append({
            "from": entity1,
            "to": entity2,
            "type": rel_type,
            "properties": props
        })
    
    socketio.emit("knowledge_graph_state", {
        "agentId": agent_id,
        "entities": entities,
        "relationships": relationships
    })


# ==================== Routes ====================

@app.route("/")
def index():
    return render_template("index.html")


# ==================== WebSocket Handlers ====================

@socketio.on("connect")
def handle_connect():
    logger.info("Client connected")
    
    # Send agents list
    persisted = agent_manager.list_persisted_agents()
    instanced = agent_manager.list_instanced_agents()
    emit("agents_list", {
        "persisted": persisted,
        "instanced": instanced
    })
    
    # Send status for all instanced agents
    for agent_info in instanced:
        emit("agent_status", agent_info)


@socketio.on("disconnect")
def handle_disconnect():
    logger.info("Client disconnected")


# ==================== Agent List ====================

@socketio.on("list_agents")
def handle_list_agents():
    """Get list of all agents (persisted and instanced)."""
    persisted = agent_manager.list_persisted_agents()
    instanced = agent_manager.list_instanced_agents()
    emit("agents_list", {
        "persisted": persisted,
        "instanced": instanced
    })


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


@socketio.on("get_agent_config")
def handle_get_config(data=None):
    """Get configuration for a specific agent."""
    agent_id = data.get("id") if data else None
    
    if agent_id:
        config = agent_manager.get_config(agent_id)
        if config:
            emit("agent_config", {
                "id": agent_id,
                **config.model_dump()
            })
            return
    
    # Return empty config for new agent
    emit("agent_config", {"id": None})


# ==================== Agent Lifecycle ====================

@socketio.on("create_agent")
def handle_create_agent(data):
    """Create a new agent and load it into memory."""
    try:
        config = AgentConfig.model_validate(data)
        agent_id = agent_manager.create_agent(config)
        
        emit_agent_status(agent_id)
        emit_agents_list()
        emit_knowledge_graph_state(agent_id)
        
        logger.info(f"Created agent {agent_id} ({config.name})")
        socketio.emit("log", {"type": "success", "message": f"Agent '{agent_id}' created"})
        
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        emit("error", {"message": str(e)})


@socketio.on("load_agent")
def handle_load_agent(data):
    """Load a persisted agent into memory."""
    agent_id = data.get("id")
    if not agent_id:
        return
    
    try:
        agent_manager.load_agent(agent_id)
        
        emit_agent_status(agent_id)
        emit_agents_list()
        emit_knowledge_graph_state(agent_id)
        
        logger.info(f"Loaded agent {agent_id}")
        socketio.emit("log", {"type": "success", "message": f"Agent '{agent_id}' loaded"})
        
    except AgentNotFoundError as e:
        logger.error(f"Agent not found: {e}")
        emit("error", {"message": f"Agent not found: {e}"})
    except AgentAlreadyInstancedError as e:
        logger.warning(f"Agent already loaded: {e}")
        emit("error", {"message": str(e)})
    except Exception as e:
        logger.error(f"Failed to load agent: {e}")
        emit("error", {"message": f"Failed to load agent: {e}"})


@socketio.on("pause_agent")
def handle_pause_agent(data):
    """Pause an agent."""
    agent_id = data.get("id")
    if not agent_id:
        return
    
    try:    
        agent_manager.pause_agent(agent_id)
        emit_agent_status(agent_id)
        emit_agents_list()
        
        socketio.emit("log", {"type": "info", "message": f"Agent '{agent_id}' paused"})
        
    except AgentNotInstancedError as e:
        logger.error(f"Agent not loaded: {e}")
        emit("error", {"message": str(e)})


@socketio.on("resume_agent")
def handle_resume_agent(data):
    """Resume a paused agent."""
    agent_id = data.get("id")
    if not agent_id:
        return
    
    try:
        agent_manager.resume_agent(agent_id)
        emit_agent_status(agent_id)
        emit_agents_list()
        
        socketio.emit("log", {"type": "success", "message": f"Agent '{agent_id}' resumed"})
        
    except AgentNotInstancedError as e:
        logger.error(f"Agent not loaded: {e}")
        emit("error", {"message": str(e)})


@socketio.on("stop_agent")
def handle_stop_agent(data):
    """Stop an agent (persist and unload)."""
    agent_id = data.get("id")
    if not agent_id:
        return
    
    agent_manager.stop_agent(agent_id)
    
    emit("agent_status", {
        "id": agent_id,
        "state": "stopped"
    }, broadcast=True)
    emit_agents_list()
    
    socketio.emit("log", {"type": "info", "message": f"Agent '{agent_id}' stopped"})


@socketio.on("delete_agent")
def handle_delete_agent(data):
    """Delete an agent completely."""
    agent_id = data.get("id")
    if not agent_id:
        return

    agent_manager.delete_agent(agent_id)
    
    emit("agent_status", {
        "id": agent_id,
        "state": "deleted"
    }, broadcast=True)
    emit_agents_list()
    
    logger.info(f"Agent {agent_id} deleted")
    socketio.emit("log", {"type": "warning", "message": f"Agent '{agent_id}' deleted"})


# ==================== Agent Configuration ====================

@socketio.on("save_agent_config")
def handle_save_config(data):
    """Save/update agent configuration."""
    agent_id = data.get("id")
    
    if not agent_id:
        # Create new agent
        try:
            config = AgentConfig.model_validate(data)
            agent_id = agent_manager.create_agent(config)
            
            emit_agent_status(agent_id)
            emit_agents_list()
            emit_knowledge_graph_state(agent_id)
            
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            emit("error", {"message": str(e)})
    else:
        # Update existing config
        try:
            config = AgentConfig.model_validate(data)
            agent_manager._save_config(agent_id, config)
            
            emit("agent_config", {"id": agent_id, **config.model_dump()})
            emit_agents_list()
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            emit("error", {"message": str(e)})


# ==================== Autonomous Mode ====================

@socketio.on("set_autonomous")
def handle_set_autonomous(data):
    """Enable/disable autonomous mode for an agent."""
    agent_id = data.get("id")
    enabled = data.get("enabled", False)
    interval = data.get("interval", 30)
    
    if not agent_id or not agent_manager.is_instanced(agent_id):
        return
    
    try:
        agent_manager.set_autonomous(agent_id, enabled, interval)
        emit_agent_status(agent_id)
        
    except AgentNotInstancedError as e:
        logger.error(f"Agent not loaded: {e}")
        emit("error", {"message": str(e)})


@socketio.on("trigger_agent_tick")
def handle_trigger_tick(data=None):
    """Manually trigger an agent tick."""
    agent_id = data.get("id") if data else None
    
    if not agent_id or not agent_manager.is_instanced(agent_id):
        return
    
    agent = agent_manager.get_agent(agent_id)
    if not agent:
        return
    
    def do_tick():
        response = agent_manager.trigger_tick(agent_id, trigger="manual")
        if response:
            socketio.emit("chat_message", {
                "agentId": agent_id,
                "user": agent.name,
                "message": response
            })
        agent_manager.process_outgoing_messages(agent_id)
    
    socketio.start_background_task(do_tick)


# ==================== Chat ====================

@socketio.on("send_message")
def handle_message(data):
    """Handle chat messages from users."""
    logger.info(f"Message: {data}")
    emit("chat_message", data, broadcast=True)
    
    user = data.get("user", "User")
    message = data.get("message", "")
    target_agent_id = data.get("agentId")
    
    # Process message with instanced agents
    for agent_info in agent_manager.list_instanced_agents():
        agent_id = agent_info["id"]
        agent_name = agent_info["name"]
        
        # Skip if targeting a different agent
        if target_agent_id and agent_id != target_agent_id:
            continue
        
        # Skip paused agents
        if agent_info["state"] == AgentState.PAUSED.value:
            continue
        
        if user != agent_name:  # Don't process agent's own messages
            def process(aid=agent_id, aname=agent_name):
                response = agent_manager.process_message(aid, user, message)
                if response:
                    socketio.emit("chat_message", {
                        "agentId": aid,
                        "user": aname,
                        "message": response
                    })
                agent_manager.process_outgoing_messages(aid)
            
            socketio.start_background_task(process)


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


# ==================== Knowledge Graph ====================

@socketio.on("get_knowledge_graph")
def handle_get_knowledge_graph(data=None):
    """Get the knowledge graph state for a specific agent."""
    agent_id = data.get("id") if data else None
    
    if agent_id and agent_manager.is_instanced(agent_id):
        emit_knowledge_graph_state(agent_id)
    else:
        for agent_info in agent_manager.list_instanced_agents():
            emit_knowledge_graph_state(agent_info["id"])


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
