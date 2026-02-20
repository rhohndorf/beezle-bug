"""
Core agent module for Beezle Bug.

This module implements the Agent class which handles LLM interactions,
tool calling, and memory management. The agent operates asynchronously
and is triggered by messages from users or event nodes.
"""

import json
import time
from loguru import logger
from datetime import datetime
from typing import Optional, Dict, Any, List
from jinja2 import Template

from beezle_bug.llm_adapter import BaseAdapter, ToolCallResult, Message
from beezle_bug.memory import MemoryStream, KnowledgeGraph, get_schema_for_prompt
from beezle_bug.tools import ToolBox
from beezle_bug.events import EventBus, EventType, Event


class Agent:
    """
    Unified agent that handles LLM interactions and tool execution.
    
    The Agent class provides a conversation interface with tool calling capabilities.
    It is triggered by messages from users, other agents, event nodes, or WaitAndCombine nodes.
    
    Agents can operate in two modes:
    - **Stateful** (with memory_stream): History is persisted to database, retrieved on each call
    - **Stateless** (no memory_stream): Only uses messages passed to execute, no persistence
    
    All operations are async to support storage-backed memory and knowledge graph.
    
    Attributes:
        name: The agent's name
        adapter: LLM adapter for generating completions
        toolbox: Collection of available tools
        memory_stream: Optional stream of conversation history
        knowledge_graph: Structured knowledge storage
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
        knowledge_graph: Optional[KnowledgeGraph] = None,
        context_size: int = 25
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
            memory_stream: Optional memory stream for persistence (stateless if None)
            knowledge_graph: Optional shared knowledge graph (creates new if None)
            context_size: Number of recent messages to load from memory (default 25)
        """
        self.id = id
        self.name = name
        self.adapter = adapter
        self.toolbox = toolbox
        self.memory_stream = memory_stream
        self.knowledge_graph = knowledge_graph if knowledge_graph is not None else KnowledgeGraph()
        self.event_bus = event_bus
        self.system_message_template = system_template
        self.context_size = context_size
        
    def _emit(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """Emit an event if event bus is configured."""
        if self.event_bus:
            self.event_bus.emit(Event(
                type=event_type,
                agent_name=self.name,
                data=data
            ))

    async def execute(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Execute the agent on incoming messages and generate a response.
        
        This is the main entry point for all agent interactions, whether from
        users, other agents, event nodes, or WaitAndCombine nodes. Implements
        the Executable protocol for use in the execution graph.
        
        Behavior depends on memory_stream presence:
        - With memory_stream: Retrieves history from DB, stores messages and responses
        - Without memory_stream: Only uses incoming messages, no persistence (stateless)
        
        Args:
            messages: List of message dicts, each with "sender" and "content" keys
            
        Returns:
            List of response message dicts with "sender" (this agent's name) and "content"
        """
        # Emit message received events
        for msg in messages:
            self._emit(EventType.MESSAGE_RECEIVED, {
                "from": msg["sender"],
                "content": msg["content"]
            })
        
        # Build system message
        system_message = self.system_message_template.render(
            agent=self,
            now=datetime.now(),
            entity_schemas=get_schema_for_prompt()
        )
        
        # Get history based on memory_stream presence
        if self.memory_stream:   
            # Store incoming messages to memory
            for msg in messages:
                await self.memory_stream.add(
                    Message(role="user", content=f"[{msg['sender']}]: {msg['content']}")
                )

            # Stateful: Query database for recent history
            recent_observations = await self.memory_stream.retrieve_recent(n=self.context_size)
            history = [obs.content for obs in recent_observations]
        else:
            # Stateless: Only use incoming messages
            history = [
                Message(role="user", content=f"[{msg['sender']}]: {msg['content']}")
                for msg in messages
            ]
        
        # Build LLM context
        llm_messages = [Message(role="system", content=system_message)] + history
        
        self._emit(EventType.LLM_CALL_STARTED, {
            "context_messages": len(llm_messages),
            "available_tools": len(self.toolbox.get_tools())
        })
        
        # Call LLM
        try:
            start_time = time.time()
            response = self.adapter.chat_completion(llm_messages, self.toolbox.get_tools())
            duration = (time.time() - start_time) * 1000
            
            response_content = getattr(response, 'content', None)
            response_reasoning = getattr(response, 'reasoning', None)
            tool_calls_count = len(response.tool_calls) if response.tool_calls else 0
            
            event_data = {
                "duration_ms": round(duration),
                "has_content": response_content is not None,
                "tool_calls": tool_calls_count,
            }
            
            if response_reasoning:
                event_data["thinking"] = response_reasoning
            
            if response_content:
                event_data["response_preview"] = (response_content[:200] + "...") if len(response_content) > 200 else response_content
            
            self._emit(EventType.LLM_CALL_COMPLETED, event_data)
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            self._emit(EventType.ERROR_OCCURRED, {"error": str(e)})
            return []

        # Store response if memory_stream exists
        if self.memory_stream:
            await self.memory_stream.add(response)
        llm_messages.append(response)

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
                        result_content = await tool.run(self)
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

                    # Store tool result if memory_stream exists
                    if self.memory_stream:
                        await self.memory_stream.add(result)
                    llm_messages.append(result)

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
                    if self.memory_stream:
                        await self.memory_stream.add(result)
                    llm_messages.append(result)
            
            # Continue thinking after tool execution
            try:
                response = self.adapter.chat_completion(llm_messages, self.toolbox.get_tools())
                if self.memory_stream:
                    await self.memory_stream.add(response)
                llm_messages.append(response)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                self._emit(EventType.ERROR_OCCURRED, {"error": str(e)})
                return []

        # Return response as list of message dicts
        if response.content:
            return [{"sender": self.name, "content": response.content}]
        return []
