from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """
    Abstract base class representing a base adapter.

    This class serves as a base for defining various adapters in a system.
    Subclasses must implement the `completion` and `chat_completion` methods
    to define the functionality of the adapter.

    Attributes:
        No attributes defined in this abstract base class.

    Methods:
        completion: Abstract method to generate completion for a given prompt
                    and grammar.
        chat_completion: Abstract method to generate completion for chat.

    Example:
        ```python

        class MyAdapter(BaseAdapter):
            def completion(self, prompt, grammar):
                # Define completion logic
                pass

            def chat_completion(self):
                # Define chat completion logic
                pass
        ```

    """

    @abstractmethod
    def completion(self, messages, grammar) -> str:
        """
        Abstract method to be implemented by subclasses.

        This method generates completion for a given prompt and grammar.

        Args:
            prompt (str): The prompt for which completion is generated.
            grammar: Additional grammar information.

        Returns:
            str: The generated completion.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.

        """
        pass

    @abstractmethod
    def chat_completion(self):
        """
        Abstract method to be implemented by subclasses.

        This method generates completion for chat.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.

        """
        pass
