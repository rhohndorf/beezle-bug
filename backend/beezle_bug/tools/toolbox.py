from typing import Dict, List, Type

from beezle_bug.tools import Tool


class ToolBox:
    def __init__(self, tools: List[Type[Tool]] = []) -> None:
        self.tools = {}
        for tool in tools:
            self.tools[tool.__name__] = tool

    def __iter__(self):
        return iter(self.tools)

    def get_tool(self, tool_name: str, args: Dict) -> Tool:
        return self.tools[tool_name](**args)

    def get_tools(self) -> list[Tool]:
        return self.tools.values()