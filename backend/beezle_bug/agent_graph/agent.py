"""
Core agent module for Beezle Bug.

This module implements the Agent class which handles LLM interactions,
tool calling, and memory management. The agent operates synchronously
and can be triggered by user messages or by a scheduler for autonomous behavior.
"""

import json
import time
from loguru import logger
from datetime import datetime
from typing import Optional, Dict, Any
from queue import Queue
from jinja2 import Template

from beezle_bug.constants import DEFAULT_MSG_BUFFER_SIZE
from beezle_bug.llm_adapter import BaseAdapter, ToolCallResult, Message
from beezle_bug.memory import MemoryStream, KnowledgeGraph, get_schema_for_prompt
from beezle_bug.tools import ToolBox
from beezle_bug.events import EventBus, EventType, Event


class Agent:
    """
    Unified agent that handles LLM interactions and tool execution.
    
    The Agent class provides a conversation interface with tool calling capabilities.
    It can be triggered by:
    - User messages (request-response model)
    - Scheduler (for autonomous/periodic behavior)
    
    Attributes:
        name: The agent's name
        adapter: LLM adapter for generating completions
        toolbox: Collection of available tools
        memory_stream: Stream of conversation history
        knowledge_graph: Structured knowledge storage
        contacts: Dictionary of contact names to message queues
        event_bus: Optional event bus for introspection
    """
    
    def __init__(
        self,
        id: str,
        name: str,
        adapter: BaseAdapter,
        toolbox: ToolBox,
        system_template: Template,
        event_bus: Optional[EventBus] = None,
        memory_stream: Optional[MemoryStream] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None
    ) -> None:
        """
        Initialize the agent.
        
        Args:
            id: Unique agent identifier
            name: Agent's display name
            adapter: LLM adapter for generating completions
            toolbox: Collection of available tools
            system_template: Jinja2 template for system message
            event_bus: Optional event bus for emitting introspection events
            memory_stream: Optional shared memory stream (creates new if None)
            knowledge_graph: Optional shared knowledge graph (creates new if None)
        """
        self.id = id
        self.name = name
        self.adapter = adapter
        self.toolbox = toolbox
        self.memory_stream = memory_stream if memory_stream is not None else MemoryStream()
        self.knowledge_graph = knowledge_graph if knowledge_graph is not None else KnowledgeGraph()
        self.contacts: Dict[str, Queue] = {}
        self.event_bus = event_bus
        self.system_message_template = system_template
        
    def _emit(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """Emit an event if event bus is configured."""
        if self.event_bus:
            self.event_bus.emit(Event(
                type=event_type,
                agent_name=self.name,
                data=data
            ))

    def add_contact(self, name: str, message_queue: Queue) -> None:
        """
        Add a contact the agent can send messages to.
        
        Args:
            name: Contact name/identifier
            message_queue: Queue to send messages to this contact
        """
        self.contacts[name] = message_queue

    def process_message(self, sender: str, content: str) -> Optional[str]:
        """
        Process an incoming message and generate a response.
        
        This is the main entry point for user-triggered interactions.
        
        Args:
            sender: Name of the message sender
            content: Message content
            
        Returns:
            Agent's response content, or None if no response
        """
        self._emit(EventType.MESSAGE_RECEIVED, {
            "from": sender,
            "content": content
        })
        
        # Add message to memory
        self.memory_stream.add(Message(role="user", content=f"[{sender}]: {content}"))
        
        # Generate response
        response = self._think()
        
        return response

    def tick(self, trigger: str = "scheduler") -> Optional[str]:
        """
        Perform one autonomous thinking cycle.
        
        This is called by the scheduler for autonomous behavior.
        The agent reviews its state and decides what to do.
        
        Args:
            trigger: What triggered this tick (for logging)
            
        Returns:
            Agent's response/action, or None if nothing to do
        """
        self._emit(EventType.LLM_CALL_STARTED, {
            "trigger": trigger,
            "context_messages": len(self.memory_stream.memories)
        })
        
        # Add a system prompt for autonomous behavior
        self.memory_stream.add(Message(
            role="system", 
            content=f"[Scheduler tick: {trigger}] Review your current state and pending tasks."
        ))
        
        response = self._think()
        
        return response

    def _think(self) -> Optional[str]:
        """
        Core thinking loop - generates LLM response and executes tools.
        
        Returns:
            Final response content, or None
        """
        # Build context with current datetime for time-aware templates
        system_message = self.system_message_template.render(
            agent=self,
            now=datetime.now(),
            entity_schemas=get_schema_for_prompt()
        )
        
        messages = [
            Message(role="system", content=system_message)
        ] + [mem.content for mem in self.memory_stream.memories[-DEFAULT_MSG_BUFFER_SIZE:]]
        
        self._emit(EventType.LLM_CALL_STARTED, {
            "context_messages": len(messages),
            "available_tools": len(self.toolbox.get_tools())
        })
        
        try:
            start_time = time.time()
            response = self.adapter.chat_completion(messages, self.toolbox.get_tools())
            duration = (time.time() - start_time) * 1000
            
            response_content = getattr(response, 'content', None)
            response_reasoning = getattr(response, 'reasoning', None)
            tool_calls_count = len(response.tool_calls) if response.tool_calls else 0
            
            event_data = {
                "duration_ms": round(duration),
                "has_content": response_content is not None,
                "tool_calls": tool_calls_count,
            }
            
            # Include thinking/reasoning if present
            if response_reasoning:
                event_data["thinking"] = response_reasoning
            
            # Include content preview
            if response_content:
                event_data["response_preview"] = (response_content[:200] + "...") if len(response_content) > 200 else response_content
            
            self._emit(EventType.LLM_CALL_COMPLETED, event_data)
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            self._emit(EventType.ERROR_OCCURRED, {"error": str(e)})
            return None

        self.memory_stream.add(response)
        messages.append(response)

        # Process tool calls
        while response.tool_calls:
            for tool_call in response.tool_calls:
                func_name = tool_call.function.name
                func_args = tool_call.function.arguments
                
                try:
                    parsed_args = json.loads(func_args)
                except:
                    parsed_args = func_args
                
                self._emit(EventType.TOOL_SELECTED, {
                    "tool_name": func_name,
                    "arguments": parsed_args
                })
                
                try:
                    tool_start = time.time()
                    
                    if func_name in self.toolbox:
                        tool = self.toolbox.get_tool(func_name, json.loads(func_args))
                        result_content = tool.run(self)
                        result = ToolCallResult(
                            tool_call_id=tool_call.id,
                            content=str(result_content),
                            role="tool"
                        )
                    else:
                        result_content = f"Tool '{func_name}' not found."
                        result = ToolCallResult(
                            tool_call_id=tool_call.id,
                            content=result_content,
                            role="tool"
                        )
                    
                    tool_duration = (time.time() - tool_start) * 1000
                    result_str = str(result_content)
                    
                    self._emit(EventType.TOOL_COMPLETED, {
                        "tool_name": func_name,
                        "duration_ms": round(tool_duration),
                        "result": result_str[:200] + "..." if len(result_str) > 200 else result_str,
                        "success": True
                    })

                    self.memory_stream.add(result)
                    messages.append(result)

                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    self._emit(EventType.TOOL_COMPLETED, {
                        "tool_name": func_name,
                        "error": str(e),
                        "success": False
                    })
                    
                    result = ToolCallResult(
                        tool_call_id=tool_call.id,
                        content=f"Error: {e}",
                        role="tool"
                    )
                    self.memory_stream.add(result)
                    messages.append(result)
            
            # Continue thinking after tool execution
            try:
                response = self.adapter.chat_completion(messages, self.toolbox.get_tools())
                self.memory_stream.add(response)
                messages.append(response)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                self._emit(EventType.ERROR_OCCURRED, {"error": str(e)})
                return None

        return response.content
