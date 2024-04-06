from typing import Dict, List, Type

from pydantic_gbnf_grammar_generator import generate_gbnf_grammar_and_documentation

from tools import Tool


class ToolBox:
    def __init__(self, tools: List[Type[Tool]] = []) -> None:
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

    def get_tool(self, function_call: Dict) -> Tool:
        func_name = function_call["function"]
        func_pars = function_call["function_parameters"]
        return self.tools[func_name](**func_pars)
