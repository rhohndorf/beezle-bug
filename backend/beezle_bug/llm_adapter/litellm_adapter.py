"""
LiteLLM adapter module for unified LLM provider access.

This module provides a unified adapter that supports 100+ LLM providers through
the LiteLLM library, including OpenAI, Anthropic, Ollama, Groq, and many more."""

import litellm
from pydantic import BaseModel

from beezle_bug.llm_adapter.base_adapter import Response


def tool_to_openai_schema(tool_cls: type[BaseModel]) -> dict:
    """
    Convert a Pydantic model to OpenAI function calling schema.
    
    This function extracts the model's JSON schema and transforms it into
    the format expected by OpenAI's function calling API.
    
    Args:
        tool_cls: A Pydantic model class representing a tool
    
    Returns:
        dict: OpenAI-compatible function schema"""
    schema = tool_cls.model_json_schema()
    
    name = tool_cls.__name__
    description = (
        tool_cls.__doc__.strip()
        if tool_cls.__doc__
        else "No description provided."
    )
    
    openai_schema = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    }

    for prop_name, prop_details in schema["properties"].items():
        openai_schema["function"]["parameters"]["properties"][prop_name] = {
            "type": prop_details.get("type", "string"),
            "description": prop_details.get("description", "No description provided.")
        }

    if "required" in schema:
        openai_schema["function"]["parameters"]["required"] = schema["required"]

    return openai_schema


def tools_to_openai_schema(tools: list[type[BaseModel]]) -> list[dict]:
    """
    Convert a list of Pydantic tool models to OpenAI schema format.
    
    Args:
        tools: List of Pydantic model classes representing tools
    
    Returns:
        list[dict]: List of OpenAI-compatible function schemas"""
    return [tool_to_openai_schema(tool) for tool in tools]


class LiteLLMAdapter:
    """
    Unified adapter for accessing 100+ LLM providers through LiteLLM.
    
    This adapter provides a consistent interface for communicating with various
    LLM providers including OpenAI, Anthropic, Cohere, Replicate, Hugging Face,
    Together AI, Azure OpenAI, PaLM, Vertex AI, Ollama, and many more.
    
    The adapter supports both simple text completions and advanced features like
    function/tool calling, streaming, and custom parameters.
    
    Attributes:
        model: Model identifier in LiteLLM format
        api_base: Optional custom API base URL
        api_key: Optional API key for authentication
        extra_params: Additional parameters passed to every completion call
    
    Args:
        model: Model identifier (e.g., 'gpt-4', 'claude-3', 'ollama/qwen3:0.6b')
        api_base: Optional custom API base URL
        api_key: Optional API key (if not set in environment variables)
        **kwargs: Additional parameters (temperature, max_tokens, etc.)
    Note:
        For a complete list of supported providers and model name formats,
        see: https://docs.litellm.ai/docs/providers"""
    
    def __init__(
        self,
        model: str,
        api_base: str = None,
        api_key: str = None,
        **kwargs
    ):
        """
        Initialize the LiteLLM adapter.
        
        Args:
            model: Model identifier in LiteLLM format
            api_base: Optional custom API base URL
            api_key: Optional API key for authentication
            **kwargs: Additional parameters for completion calls"""
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        self.extra_params = kwargs
        
        if api_base:
            litellm.api_base = api_base
        if api_key:
            litellm.api_key = api_key

    def chat_completion(self, messages, tools) -> Response:
        """
        Generate a chat completion with optional tool/function calling support.
        
        This method sends messages to the LLM and receives a response that may
        include tool calls. It handles message format conversion and response
        parsing automatically.
        
        Args:
            messages: List of message dictionaries or Message objects
            tools: List of Pydantic tool model classes
        
        Returns:
            Response: Response object containing content, role, and tool calls"""
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, 'model_dump'):
                formatted_messages.append(msg.model_dump())
            elif hasattr(msg, 'dict'):
                formatted_messages.append(msg.dict())
            else:
                formatted_messages.append(msg)
        
        completion_params = {
            "model": self.model,
            "messages": formatted_messages,
            **self.extra_params
        }
        
        if tools:
            completion_params["tools"] = tools_to_openai_schema(tools)
        
        if self.api_base:
            completion_params["api_base"] = self.api_base
        if self.api_key:
            completion_params["api_key"] = self.api_key
        
        response = litellm.completion(**completion_params)
        
        message = response.choices[0].message
        
        response_dict = {
            "content": message.content,
            "role": message.role,
            "reasoning": "",  # LiteLLM doesn't provide reasoning field
            "tool_calls": []
        }
        
        if hasattr(message, 'tool_calls') and message.tool_calls:
            response_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        
        return Response.model_validate(response_dict)

    def completion(self, messages, grammar=None) -> str:
        """
        Generate a simple text completion without tool calling.
        
        This method provides basic text generation from a list of messages.
        The grammar parameter is kept for interface compatibility but is
        ignored as most LiteLLM providers don't support grammar-constrained
        generation.
        
        Args:
            messages: List of message dictionaries or Message objects
            grammar: Ignored (kept for backward compatibility)
        
        Returns:
            str: The generated completion text
        Note:
            For grammar-constrained generation, consider using specialized
            adapters or libraries like llama.cpp with GBNF grammars."""
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, 'model_dump'):
                formatted_messages.append(msg.model_dump())
            elif hasattr(msg, 'dict'):
                formatted_messages.append(msg.dict())
            else:
                formatted_messages.append(msg)
        
        completion_params = {
            "model": self.model,
            "messages": formatted_messages,
            **self.extra_params
        }
        
        if self.api_base:
            completion_params["api_base"] = self.api_base
        if self.api_key:
            completion_params["api_key"] = self.api_key
        
        response = litellm.completion(**completion_params)
        
        return response.choices[0].message.content
