"""
Executable protocol for the agent graph execution system.

Any node that processes messages in the execution graph must implement this protocol.
"""

from typing import Protocol


class Executable(Protocol):
    """Protocol for nodes that process messages in the execution graph.
    
    This is the core interface for any node that can be part of the message
    processing pipeline. Currently implemented by Agent, but designed to
    support future logic nodes (conditionals, transforms, etc.).
    """
    id: str
    name: str
    
    async def execute(self, messages: list[dict]) -> list[dict]:
        """Process input messages and return output messages.
        
        Args:
            messages: List of message dicts, each with "sender" and "content" keys
            
        Returns:
            List of output message dicts, or empty list if no output
        """
        ...
