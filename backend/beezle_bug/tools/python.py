"""
Python code execution tool using embedded IPython shells.

Each agent gets its own IPython InteractiveShell instance that persists
variables, functions, and imports across multiple code execution calls.
"""

from typing import Dict
from io import StringIO
from pydantic import Field

from IPython.core.interactiveshell import InteractiveShell

from beezle_bug.tools import Tool


# Module-level registry of per-agent IPython shells
_agent_shells: Dict[str, InteractiveShell] = {}


def get_shell(agent_id: str) -> InteractiveShell:
    """
    Get or create an IPython shell for the given agent.
    
    Args:
        agent_id: The unique identifier for the agent
        
    Returns:
        The agent's IPython InteractiveShell instance
    """
    if agent_id not in _agent_shells:
        shell = InteractiveShell.instance()
        # Create a fresh instance for this agent
        shell = InteractiveShell()
        _agent_shells[agent_id] = shell
    return _agent_shells[agent_id]


def cleanup_shell(agent_id: str) -> None:
    """
    Clean up and remove an agent's IPython shell.
    
    Args:
        agent_id: The unique identifier for the agent
    """
    if agent_id in _agent_shells:
        del _agent_shells[agent_id]


class ExecPythonCode(Tool):
    """
    Execute Python code in a persistent IPython session.
    
    The session maintains state across calls - variables, functions,
    and imports defined in one call are available in subsequent calls.
    """

    code: str = Field(description="Python code to execute")

    def run(self, agent) -> str:
        """
        Execute the code in the agent's IPython shell.
        
        Args:
            agent: The agent executing this tool (provides agent.id)
            
        Returns:
            String containing stdout, stderr, and execution result
        """
        shell = get_shell(agent.id)
        
        # Capture output
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        # Store original streams
        import sys
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        try:
            # Redirect output
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # Execute the code
            result = shell.run_cell(self.code, store_history=True)
            
        finally:
            # Restore streams
            sys.stdout = original_stdout
            sys.stderr = original_stderr
        
        # Build output string
        output_parts = []
        
        stdout_content = stdout_capture.getvalue()
        if stdout_content:
            output_parts.append(stdout_content.rstrip())
        
        stderr_content = stderr_capture.getvalue()
        if stderr_content:
            output_parts.append(f"[stderr]\n{stderr_content.rstrip()}")
        
        # Check for execution errors
        if result.error_in_exec is not None:
            error_msg = f"[error] {type(result.error_in_exec).__name__}: {result.error_in_exec}"
            output_parts.append(error_msg)
        
        # Include the result if there is one (and it's not None)
        if result.result is not None:
            output_parts.append(f">>> {repr(result.result)}")
        
        if not output_parts:
            return "Code executed successfully (no output)"
        
        return "\n".join(output_parts)
