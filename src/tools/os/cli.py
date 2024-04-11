import subprocess

from pydantic import Field

from tools import Tool


class ExecCommand(Tool):
    """
    Execute a shell command
    """

    command: str = Field(..., description="The command to be executed")

    def run(self, agent):
        return subprocess.run(self.command, capture_output=True, text=True)
