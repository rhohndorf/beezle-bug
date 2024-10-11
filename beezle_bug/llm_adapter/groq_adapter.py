from enum import Enum
import json
import logging
import os
from typing import Any, Type, Union

from pydantic import BaseModel
from groq import Groq

from beezle_bug.llm_adapter import BaseAdapter
from beezle_bug.memory import Observation
from beezle_bug.tools import Tool, ToolBox

DEFAULT_MODEL = "mixtral-8x7b-32768"
TYPEMAP = {
    Any: {"type": "any"},
    str: {"type": "string"},
    float: {"type": "number"},
    int: {"type": "integer"},
    bool: {"type": "boolean"},
    list: {"type": "array"},
}


class GroqApiAdapter(BaseAdapter):
    def __init__(self) -> None:
        self.client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )
        super().__init__()

    def completion(self, prompt, grammar) -> str:
        return ""

    def chat_completion(self, messages: list[Observation], tools: ToolBox) -> str:
        response = self.client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[message.model_dump() for message in messages],
            tools=_translate_tools(tools),
            tool_choice="required",
        )
        logging.debug(response)
        return _process_output(response)


def _process_output(response):
    tool_call = response.choices[0].message.tool_calls[0]
    logging.debug(tool_call)
    arguments = json.loads(tool_call.function.arguments)
    name = tool_call.function.name
    return {
        "function": name,
        "function_parameters": arguments,
        "id": tool_call.id,
    }


def _translate_tools(toolbox: ToolBox) -> list[dict]:
    tools = []
    for tool in toolbox.get_tools():
        tools.append(get_openai_tool_def(tool))
    return tools


# def get_openai_type(py_type):
#     """Map Python types to JSON schema types and handle special cases like Enums, Lists, and Unions."""
#     if inspect.isclass(py_type) and issubclass(py_type, Enum):
#         # Handle Enum types by determining their actual value types
#         return get_enum_type(py_type)
#     elif inspect.isclass(py_type) and issubclass(py_type, BaseModel):
#         # Handle nested Pydantic models by recursive call
#         return {
#             "type": "object",
#             "properties": pydantic_model_to_openai_function_definition(py_type)["function"]["parameters"]["properties"],
#         }
#     elif hasattr(py_type, "__origin__"):
#         if py_type.__origin__ is Union:
#             # Filter out NoneType to handle optional fields
#             non_none_types = [t for t in py_type.__args__ if t is not type(None)]
#             return get_openai_type(non_none_types[0])
#         elif py_type.__origin__ is list or py_type.__origin__ is list:
#             # Handle lists by identifying the type of list items
#             return {"type": "array", "items": get_openai_type(py_type.__args__[0])}
#     else:
#         # Default type handling
#         return py_type_to_json_type(py_type)


def get_openai_tool_def(pydantic_model: Tool):
    model_schema = pydantic_model.model_json_schema()
    print(model_schema)
    properties = model_schema["properties"]
    required_fields = model_schema.get("required", [])
    class_doc = pydantic_model.__doc__

    function_definition = {
        "type": "function",
        "function": {
            "name": pydantic_model.__name__,
            "description": class_doc,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": required_fields,
            },
        },
    }

    # type_hints = typing.get_type_hints(pydantic_model)
    # for prop_name, prop_meta in properties.items():
    #     prop_type = type_hints[prop_name]

    #     openai_type = get_openai_type(prop_type)
    #     field_info = pydantic_model.model_fields.get(prop_name)
    #     field_description = field_info.description if field_info and field_info.description else ""
    #     if isinstance(openai_type, dict) and "union" in openai_type.get("type", ""):
    #         # Handling Union types specifically
    #         function_definition["function"]["parameters"]["properties"][prop_name] = {
    #             "type": "union",
    #             "options": openai_type["options"],
    #             "description": field_description,
    #         }
    #     else:
    #         function_definition["function"]["parameters"]["properties"][prop_name] = {
    #             **openai_type,
    #             "description": field_description,
    #         }

    return function_definition
