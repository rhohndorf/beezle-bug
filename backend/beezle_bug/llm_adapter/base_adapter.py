"""
Base adapter module for LLM integrations.

This module provides abstract base classes and data models for implementing
LLM adapters that can communicate with various language model providers."""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class Function(BaseModel):
    """
    Represents a function call definition.
    
    Attributes:
        name: The name of the function to call
        arguments: JSON string containing the function arguments"""
    name: str
    arguments: str


class ToolCall(BaseModel):
    """
    Represents a tool/function call request from the LLM.
    
    Attributes:
        id: Unique identifier for this tool call
        function: The function details (name and arguments)
        type: The type of tool call (typically "function")"""
    id: str
    function: Function
    type: str


class Response(BaseModel):
    """
    Represents a response from the LLM.
    
    Attributes:
        content: The text content of the response (None if only tool calls)
        role: The role of the responder (typically "assistant")
        reasoning: Optional reasoning or chain-of-thought explanation
        tool_calls: List of tool calls requested by the LLM"""
    content: Optional[str]
    role: str
    reasoning: Optional[str] = ""
    tool_calls: Optional[list[ToolCall]] = []


class ToolCallResult(BaseModel):
    """
    Represents the result of a tool/function execution.
    
    Attributes:
        role: The role identifier (always "tool")
        tool_call_id: ID of the tool call this result corresponds to
        content: The result content from the tool execution"""
    role: str = "tool"
    tool_call_id: str
    content: str


class Message(BaseModel):
    """
    Represents a message in a conversation.
    
    Attributes:
        role: The role of the message sender (e.g., "user", "assistant", "system")
        content: The text content of the message"""
    role: str
    content: str


class BaseAdapter(ABC):
    """
    Abstract base class for LLM adapters.
    
    This class defines the interface that all LLM adapters must implement.
    Subclasses should provide concrete implementations for communicating with
    specific LLM providers.
    
    Methods:
        completion: Generate a text completion from messages
        chat_completion: Generate a chat completion with optional tool calling"""

    @abstractmethod
    def completion(self, messages, grammar) -> str:
        """
        Generate a text completion from a list of messages.
        
        Args:
            messages: List of conversation messages
            grammar: Optional grammar constraints for generation
        
        Returns:
            str: The generated completion text
        
        Raises:
            NotImplementedError: This method must be implemented by subclasses"""
        pass

    @abstractmethod
    def chat_completion(self, messages, tools) -> Response:
        """
        Generate a chat completion with optional tool calling support.
        
        Args:
            messages: List of conversation messages
            tools: List of available tools/functions the LLM can call
        
        Returns:
            Response: Response object containing the completion and any tool calls
        
        Raises:
            NotImplementedError: This method must be implemented by subclasses"""
        pass
