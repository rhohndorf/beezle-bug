from typing import Optional, Any
from abc import ABC, abstractmethod
from pydantic import BaseModel


class Tool(ABC, BaseModel):
    """
    Abstract base class representing a tool.

    This class serves as a base for defining various tools in a system.
    Subclasses must implement the `run` method to define the functionality
    of the tool.

    Attributes:
        No attributes defined in this abstract base class.

    Methods:
        run: Abstract method that must be implemented by subclasses to define
             the functionality of the tool.

    Example:
        ```python
        from abc import ABC, abstractmethod
        from pydantic import BaseModel

        class MyTool(Tool):
            def run(self):
                # Define functionality of the tool
                pass
        ```

    """

    @abstractmethod
    def run(self, agent) -> Optional[Any]:
        """
        Abstract method to be implemented by subclasses.

        This method defines the functionality of the tool. Subclasses must
        override this method to provide specific implementation.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.

        """
        pass
