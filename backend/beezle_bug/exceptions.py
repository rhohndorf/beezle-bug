"""
Beezle Bug Exceptions.

Custom exceptions for agent management and operations.
"""


class AgentNotFoundError(Exception):
    """Raised when an agent doesn't exist on disk."""
    pass


class AgentAlreadyInstancedError(Exception):
    """Raised when trying to load an agent that's already in memory."""
    pass


class AgentNotInstancedError(Exception):
    """Raised when trying to operate on an agent that's not in memory."""
    pass

