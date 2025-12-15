from typing import Optional, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel


class Tool(ABC, BaseModel):
    """
    Abstract base class representing a tool.

    This class serves as a base for defining various tools in a system.
    Subclasses must implement the `run` method to define the functionality
    of the tool.

    All tool run methods are async to support async storage operations.

    Attributes:
        No attributes defined in this abstract base class.

    Methods:
        run: Abstract async method that must be implemented by subclasses to define
             the functionality of the tool.

    Example:
        ```python
        from beezle_bug.tools import Tool

        class MyTool(Tool):
            async def run(self, agent):
                # Define functionality of the tool
                return "result"
        ```

    """

    @abstractmethod
    async def run(self, agent) -> Optional[Any]:
        """
        Abstract async method to be implemented by subclasses.

        This method defines the functionality of the tool. Subclasses must
        override this method to provide specific implementation.

        Args:
            agent: The agent executing this tool

        Returns:
            The result of the tool execution

        Raises:
            NotImplementedError: This method must be implemented by subclasses.

        """
        pass
