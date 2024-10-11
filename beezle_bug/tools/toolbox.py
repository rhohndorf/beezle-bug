from typing import Type

from pydantic_gbnf_grammar_generator import generate_gbnf_grammar_and_documentation

from beezle_bug.tools.tool import Tool


class ToolBox:
    def __init__(self, tools: list[Type[Tool]] = []) -> None:
        self.tools = {}
        for tool in tools:
            self.tools[tool.__name__] = tool

        self.grammar, self.docs = generate_gbnf_grammar_and_documentation(
            list(self.tools.values()),
            outer_object_name="function",
            outer_object_content="function_parameters",
            model_prefix="Function",
            fields_prefix="Parameters",
        )

    def get_tool(self, function_call: dict) -> Tool:
        func_name = function_call["function"]
        func_pars = function_call["function_parameters"]
        return self.tools[func_name](**func_pars)

    def get_tools(self) -> list[Tool]:
        return list(self.tools.values())
