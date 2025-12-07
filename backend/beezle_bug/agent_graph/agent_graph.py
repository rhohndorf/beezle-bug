"""
AgentGraph class - the domain model for a graph of connected nodes.
"""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from .types import EdgeType
from .node import Node
from .edge import Edge


class AgentGraph(BaseModel):
    """A graph of connected nodes representing an agent graph."""
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_edges_for_node(self, node_id: str) -> list[Edge]:
        """Get all edges connected to a node."""
        return [
            edge for edge in self.edges
            if edge.source_node == node_id or edge.target_node == node_id
        ]

    def get_connected_nodes(self, node_id: str, edge_type: Optional[EdgeType] = None) -> list[Node]:
        """Get all nodes connected to a given node, optionally filtered by edge type."""
        connected = []
        for edge in self.edges:
            if edge_type and edge.edge_type != edge_type:
                continue
            if edge.source_node == node_id:
                node = self.get_node(edge.target_node)
                if node:
                    connected.append(node)
            elif edge.target_node == node_id:
                node = self.get_node(edge.source_node)
                if node:
                    connected.append(node)
        return connected

    def add_node(self, node: Node) -> None:
        """Add a node to the agent graph."""
        self.nodes.append(node)

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its edges from the agent graph."""
        self.nodes = [n for n in self.nodes if n.id != node_id]
        self.edges = [
            e for e in self.edges
            if e.source_node != node_id and e.target_node != node_id
        ]

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the agent graph."""
        self.edges.append(edge)

    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the agent graph."""
        self.edges = [e for e in self.edges if e.id != edge_id]

    # Persistence methods

    def save(self, path: Path) -> None:
        """Save the agent graph to a JSON file."""
        with open(path, "w") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "AgentGraph":
        """Load an agent graph from a JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.model_validate(data)

