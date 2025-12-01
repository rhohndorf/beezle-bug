"""
LLM configuration module for chat message formatting.

This module provides configuration classes for different LLM formats,
defining message delimiters and header markers for various model families."""

import beezle_bug.template as template


DEFAULT_TEMPLATE = "default_prompt"


class LlmConfig:
    """
    Configuration for LLM message formatting.
    
    Different LLM families use different special tokens to mark message
    boundaries and role headers. This class encapsulates those formats.
    
    Attributes:
        msg_start: Token marking the start of a message
        msg_stop: Token marking the end of a message
        hdr_start: Token marking the start of a role header (optional)
        hdr_stop: Token marking the end of a role header (optional)
        template: Jinja2 template for rendering full prompts"""
    
    def __init__(
        self,
        msg_start: str,
        msg_stop: str,
        hdr_start: str = "",
        hdr_stop: str = "",
    ) -> None:
        """
        Initialize LLM configuration.
        
        Args:
            msg_start: Token to start each message
            msg_stop: Token to end each message
            hdr_start: Token to start role headers (default: "")
            hdr_stop: Token to end role headers (default: "")"""
        self.msg_start = msg_start
        self.msg_stop = msg_stop
        self.hdr_start = hdr_start
        self.hdr_stop = hdr_stop
        self.template = template.load(DEFAULT_TEMPLATE)


CHATML = LlmConfig(
    msg_start="<|im_start|>",
    msg_stop="<|im_end|>"
)


GEMMA = LlmConfig(
    msg_start="<start_of_turn>",
    msg_stop="<end_of_turn>"
)


LLAMA = LlmConfig(
    msg_start="",
    msg_stop="<|eot_id|>",
    hdr_start="<|start_header_id|>",
    hdr_stop="<|stop_header_id|>"
)
