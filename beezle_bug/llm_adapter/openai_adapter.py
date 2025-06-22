import json
from pydantic import BaseModel
from openai import OpenAI

def tool_to_openai_schema(tool_cls: type[BaseModel]) -> str:
    schema = tool_cls.schema()
    
    # Extract function name and description
    name = tool_cls.__name__
    description = tool_cls.__doc__.strip() if tool_cls.__doc__ else "No description provided."
    
    # Construct OpenAI-compatible schema
    openai_schema = {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }

    for prop_name, prop_details in schema["properties"].items():
        openai_schema["parameters"]["properties"][prop_name] = {
            "type": prop_details.get("type", "string"),
            "description": prop_details.get("description", "No description provided.")
        }

    if "required" in schema:
        openai_schema["parameters"]["required"] = schema["required"]
    
    return openai_schema


def tools_to_openai_schema(tools):
    return [tool_to_openai_schema(tool) for tool in tools]
        

class OpenAiAdapter():
    def __init__(self, model, api_url=None, api_key=""):
        super().__init__()
        if api_url:
            self.client = OpenAI(base_url=api_url, api_key=api_key)
        else:
            self.client = OpenAI(api_key=api_key)
        self.model = model

    def chat_completion(self, messages, tools):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools_to_openai_schema(tools)
        )

        return response.choices[0].message.content


