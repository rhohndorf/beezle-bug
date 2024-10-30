from pydantic import Field

from beezle_bug.tools import Tool


class ExecPythonCode(Tool):
    """
    Execute a piece of Python code and return the result.
    """

    code: str = Field(description="Python Code to execute")

    def run(self, agent):
        return eval(self.code)
