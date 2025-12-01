"""
Toolbox Factory for creating tool collections.

Provides a registry of all available tools and factory methods
to create toolboxes with selected tools.
"""

from typing import List

from beezle_bug.tools import ToolBox

# Messaging tools
from beezle_bug.tools.messaging import SendMessage

# System tools
from beezle_bug.tools.system import (
    Wait,
    Reason,
    SetEngagement,
    SelfReflect,
    SelfCritique,
    GetDateAndTime,
)

# Python tools
from beezle_bug.tools.python import ExecPythonCode

# Task tools
from beezle_bug.tools.tasks import MakePlan, CreateTask

# Web tools
from beezle_bug.tools.web import ReadWebsite, SearchWeb, SearchNews

# Wikipedia tools
from beezle_bug.tools.wikipedia import SearchWikipedia, GetWikipediaPageSummary

# Memory tools - Knowledge Graph
from beezle_bug.tools.memory.knowledge_graph import (
    AddEntity,
    AddPropertyToEntity,
    AddRelationship,
    GetEntity,
    GetRelationships,
    RemoveRelationship,
    RemoveEntity,
    RemoveEntityProperty,
    AddPropertyToRelationship,
    GetRelationship,
    RemoveRelationshipProperty,
    FindEntitiesByType,
    FindEntitiesByProperty,
    FindRelationshipsByType,
    GetNeighbors,
    FindPath,
    GetConnectedEntities,
    GetMostConnected,
    GetIsolatedEntities,
    CheckGraphConnectivity,
)

# Memory tools - Memory Stream
from beezle_bug.tools.memory.memory_stream import Recall

# Filesystem tools
from beezle_bug.tools.os.filesystem import WriteTextFile, ReadTextFile, GetFileList

# OS tools
from beezle_bug.tools.os.cli import ExecCommand


class ToolboxFactory:
    """Factory for creating toolboxes with selected tools."""
    
    # Registry mapping tool names to tool classes
    registry = {
        # Messaging
        "send_message": SendMessage,
        
        # System
        "wait": Wait,
        "reason": Reason,
        "set_engagement": SetEngagement,
        "self_reflect": SelfReflect,
        "self_critique": SelfCritique,
        "get_date_time": GetDateAndTime,
        
        # Python
        "exec_python": ExecPythonCode,
        
        # Tasks
        "make_plan": MakePlan,
        "create_task": CreateTask,
        
        # Web
        "read_website": ReadWebsite,
        "search_web": SearchWeb,
        "search_news": SearchNews,
        
        # Wikipedia
        "search_wikipedia": SearchWikipedia,
        "wikipedia_summary": GetWikipediaPageSummary,
        
        # Knowledge Graph - CRUD
        "kg_add_entity": AddEntity,
        "kg_add_property": AddPropertyToEntity,
        "kg_add_relationship": AddRelationship,
        "kg_get_entity": GetEntity,
        "kg_get_relationships": GetRelationships,
        "kg_remove_relationship": RemoveRelationship,
        "kg_remove_entity": RemoveEntity,
        "kg_remove_entity_property": RemoveEntityProperty,
        "kg_add_relationship_property": AddPropertyToRelationship,
        "kg_get_relationship": GetRelationship,
        "kg_remove_relationship_property": RemoveRelationshipProperty,
        
        # Knowledge Graph - Query
        "kg_find_by_type": FindEntitiesByType,
        "kg_find_by_property": FindEntitiesByProperty,
        "kg_find_relationships_by_type": FindRelationshipsByType,
        "kg_get_neighbors": GetNeighbors,
        "kg_find_path": FindPath,
        "kg_get_connected": GetConnectedEntities,
        "kg_most_connected": GetMostConnected,
        "kg_isolated_entities": GetIsolatedEntities,
        "kg_check_connectivity": CheckGraphConnectivity,
        
        # Memory Stream
        "recall": Recall,
        
        # Filesystem
        "write_file": WriteTextFile,
        "read_file": ReadTextFile,
        "list_files": GetFileList,
        
        # OS
        "exec_command": ExecCommand,
    }
    
    # Predefined tool sets
    PRESETS = {
        "minimal": [
            "send_message", "wait", "reason", "get_date_time"
        ],
        "standard": [
            "send_message", "wait", "reason", "self_reflect", "get_date_time",
            "recall", "search_web", "read_website"
        ],
        "research": [
            "send_message", "wait", "reason", "self_reflect", "get_date_time",
            "recall", "search_web", "search_news", "read_website",
            "search_wikipedia", "wikipedia_summary"
        ],
        "knowledge_extractor": [
            "send_message", "wait", "reason", "get_date_time", "recall",
            "kg_add_entity", "kg_add_property", "kg_add_relationship",
            "kg_get_entity", "kg_get_relationships",
            "kg_remove_relationship", "kg_remove_entity", "kg_remove_entity_property",
            "kg_add_relationship_property", "kg_get_relationship", "kg_remove_relationship_property",
            "kg_find_by_type", "kg_find_by_property", "kg_find_relationships_by_type",
            "kg_get_neighbors", "kg_find_path", "kg_get_connected",
            "kg_most_connected", "kg_isolated_entities", "kg_check_connectivity"
        ],
        "developer": [
            "send_message", "wait", "reason", "self_reflect", "get_date_time",
            "recall", "search_web", "read_website",
            "exec_python", "write_file", "read_file", "list_files", "exec_command"
        ],
        "full": list(registry.keys())
    }
    
    def __call__(self, tools: List[str]) -> ToolBox:
        """
        Create a toolbox with the specified tools.
        
        Args:
            tools: List of tool names or preset name.
                   If a single preset name is given, uses that preset.
                   Otherwise, creates toolbox with specified tools.
        
        Returns:
            ToolBox with the specified tools.
        """
        # Check if it's a preset
        if len(tools) == 1 and tools[0] in self.PRESETS:
            tool_names = self.PRESETS[tools[0]]
        else:
            tool_names = tools
        
        # Build tool classes list
        tool_classes = []
        for name in tool_names:
            if name in self.registry:
                tool_classes.append(self.registry[name])
            else:
                raise ValueError(f"Unknown tool: {name}. Available tools: {list(self.registry.keys())}")
        
        return ToolBox(tool_classes)
    
    @classmethod
    def list_tools(cls) -> List[str]:
        """Return list of all available tool names."""
        return list(cls.registry.keys())
    
    @classmethod
    def list_presets(cls) -> List[str]:
        """Return list of available preset names."""
        return list(cls.PRESETS.keys())
    
    @classmethod
    def get_preset(cls, name: str) -> List[str]:
        """Return list of tools in a preset."""
        if name not in cls.PRESETS:
            raise ValueError(f"Unknown preset: {name}. Available: {list(cls.PRESETS.keys())}")
        return cls.PRESETS[name]
