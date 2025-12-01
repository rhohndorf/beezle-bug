"""
[DEPRECATED] OpenAI adapter module.

This module is deprecated and will be removed in a future version.
Please use LiteLLMAdapter instead for better provider support and features.

See LITELLM_MIGRATION.md for migration instructions."""

import warnings

from pydantic import BaseModel
from openai import OpenAI

from beezle_bug.llm_adapter import Response


warnings.warn(
    "OpenAiAdapter is deprecated. Please use LiteLLMAdapter instead. "
    "See LITELLM_MIGRATION.md for migration instructions.",
    DeprecationWarning,
    stacklevel=2
)


def tool_to_openai_schema(tool_cls: type[BaseModel]) -> dict:
    """
    Convert a Pydantic model to OpenAI function schema.
    
    Args:
        tool_cls: Pydantic model class representing a tool
    
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
    Convert list of Pydantic tools to OpenAI schema format.
    
    Args:
        tools: List of Pydantic model classes
    
    Returns:
        list[dict]: List of OpenAI-compatible function schemas"""
    return [tool_to_openai_schema(tool) for tool in tools]


class OpenAiAdapter:
    """
    [DEPRECATED] Adapter for OpenAI API and compatible endpoints.
    
    This adapter is deprecated. Use LiteLLMAdapter instead for better
    provider support, more features, and active maintenance.
    
    Args:
        model: Model identifier
        api_url: Optional custom API URL
        api_key: API key for authentication"""
    
    def __init__(self, model: str, api_url: str = None, api_key: str = ""):
        """
        Initialize the OpenAI adapter.
        
        Args:
            model: Model identifier (e.g., 'gpt-4')
            api_url: Optional custom API base URL
            api_key: API key for authentication"""
        super().__init__()
        
        if api_url:
            self.client = OpenAI(base_url=api_url, api_key=api_key)
        else:
            self.client = OpenAI(api_key=api_key)
        
        self.model = model

    def chat_completion(self, messages, tools) -> Response:
        """
        Generate a chat completion with tool calling support.
        
        Args:
            messages: List of conversation messages
            tools: List of available tools
        
        Returns:
            Response: Response object with content and tool calls"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools_to_openai_schema(tools)
        )
        
        message = response.choices[0].message
        message_dict = message.model_dump()
        
        # Extract reasoning/thinking if present (some models like Claude, o1 provide this)
        # Check for common reasoning field names
        reasoning = None
        if hasattr(message, 'reasoning'):
            reasoning = message.reasoning
        elif hasattr(message, 'thinking'):
            reasoning = message.thinking
        elif hasattr(response.choices[0], 'reasoning'):
            reasoning = response.choices[0].reasoning
        
        # Some local models put thinking in <think> tags in content
        content = message_dict.get('content', '')
        if content and '<think>' in content and '</think>' in content:
            import re
            think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
            if think_match:
                reasoning = think_match.group(1).strip()
                # Remove thinking from content
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                message_dict['content'] = content
        
        message_dict['reasoning'] = reasoning
        
        return Response.model_validate(message_dict)
