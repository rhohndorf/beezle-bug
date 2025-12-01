"""
[DEPRECATED] Llama.cpp API adapter module.

This module is deprecated and will be removed in a future version.
Please use LiteLLMAdapter instead for better provider support and features.

See LITELLM_MIGRATION.md for migration instructions."""

import warnings
from loguru import logger

import requests

from beezle_bug.llm_adapter import BaseAdapter


warnings.warn(
    "LlamaCppApiAdapter is deprecated. Please use LiteLLMAdapter instead. "
    "See LITELLM_MIGRATION.md for migration instructions.",
    DeprecationWarning,
    stacklevel=2
)


DEFAULT_URL = "http://localhost"
DEFAULT_PORT = 8080


class LlamaCppApiAdapter(BaseAdapter):
    """
    [DEPRECATED] Adapter for llama.cpp HTTP server API.
    
    This adapter communicates with a llama.cpp server running in API mode.
    It is deprecated in favor of LiteLLMAdapter which provides better
    compatibility and more features.
    
    Args:
        llm_config: LLM configuration object
        url: Server URL (default: http://localhost)
        port: Server port (default: 8080)
    
    Note:
        For llama.cpp servers with OpenAI-compatible endpoints, use
        LiteLLMAdapter with api_base='http://localhost:8080/v1' instead."""
    
    def __init__(
        self,
        llm_config,
        url: str = DEFAULT_URL,
        port: int = DEFAULT_PORT
    ) -> None:
        """
        Initialize the llama.cpp adapter.
        
        Args:
            llm_config: Configuration object containing template and stop tokens
            url: Server URL
            port: Server port"""
        self.llm_config = llm_config
        self.url = url
        self.port = port
        super().__init__()

    def completion(self, messages, grammar) -> str:
        """
        Generate a text completion with optional grammar constraints.
        
        Args:
            messages: List of conversation messages
            grammar: GBNF grammar for constrained generation
        
        Returns:
            str: Generated completion text"""
        endpoint_url = f"{self.url}:{self.port}/completion"
        
        headers = {"Content-Type": "application/json"}
        
        prompt = self.llm_config.template.render(
            llm=self.llm_config,
            messages=messages
        )
        logger.debug(prompt)
        
        data = {
            "prompt": prompt,
            "grammar": grammar,
            "stop": self.llm_config.msg_stop
        }
        
        response = requests.post(endpoint_url, headers=headers, json=data)
        
        data = response.json()
        return data["content"]

    def chat_completion(self, messages, tools):
        """
        Chat completion is not implemented for llama.cpp adapter.
        
        This method is required by BaseAdapter but not implemented.
        Use LiteLLMAdapter for full chat completion support.
        
        Args:
            messages: List of conversation messages
            tools: List of available tools
        
        Raises:
            NotImplementedError: This method is not implemented"""
        raise NotImplementedError(
            "chat_completion is not implemented for LlamaCppApiAdapter. "
            "Please use LiteLLMAdapter instead."
        )
