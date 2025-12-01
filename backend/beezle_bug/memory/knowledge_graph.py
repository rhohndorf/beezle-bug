"""
Knowledge graph module for structured information storage.

This module implements a knowledge graph using NetworkX for graph operations,
providing efficient traversal, path finding, and query capabilities.
"""

import json
from typing import Optional, List, Dict, Any, Set
import networkx as nx


class KnowledgeGraph:
    """
    A knowledge graph for storing structured information using NetworkX.
    
    The knowledge graph stores:
    - Entities: Named nodes with properties (key-value pairs)
    - Relationships: Directed edges between entities with optional properties
    
    This provides structured storage separate from the conversational
    memory stream, useful for facts, concepts, and their relationships.
    
    Attributes:
        graph: NetworkX DiGraph storing entities as nodes and relationships as edges
    """
    
    def __init__(self):
        """Initialize an empty knowledge graph."""
        self.graph = nx.DiGraph()

    # ========== Entity Operations ==========
    
    def add_entity(self, entity: str, properties: dict) -> str:
        """
        Add a new entity with properties to the graph.
        
        Args:
            entity: Unique name for the entity
            properties: Dictionary of property-value pairs
        
        Returns:
            str: Success message or error if entity already exists
        """
        if self.graph.has_node(entity):
            return f"Error: Entity '{entity}' already exists."

        self.graph.add_node(entity, **properties)
        return f"Entity '{entity}' added successfully."

    def add_entity_property(self, entity: str, property: str, value: str) -> str:
        """
        Add or update a property on an existing entity.
        
        Args:
            entity: Name of the entity
            property: Property name
            value: Property value
        
        Returns:
            str: Success message or error if entity doesn't exist
        """
        if not self.graph.has_node(entity):
            return f"Error: Entity '{entity}' does not exist."

        self.graph.nodes[entity][property] = value
        return f"Property {property} set to {value} on entity {entity}"

    def get_entity(self, entity: str) -> dict | str:
        """
        Retrieve the properties of an entity.
        
        Args:
            entity: Name of the entity to retrieve
        
        Returns:
            dict: Entity properties, or error message if not found
        """
        if not self.graph.has_node(entity):
            return f"Error: Entity '{entity}' not found."
        return dict(self.graph.nodes[entity])

    def remove_entity(self, entity: str) -> str:
        """
        Remove an entity and all its relationships from the graph.
        
        Args:
            entity: Name of the entity to remove
        
        Returns:
            str: Success message or error if entity doesn't exist
        """
        if not self.graph.has_node(entity):
            return f"Error: Entity '{entity}' does not exist."

        self.graph.remove_node(entity)
        return f"Entity '{entity}' and all its relationships removed successfully."

    def remove_entity_property(self, entity: str, property: str) -> str:
        """
        Remove a property from an entity.
        
        Args:
            entity: Name of the entity
            property: Property name to remove
        
        Returns:
            str: Success message or error if entity/property doesn't exist
        """
        if not self.graph.has_node(entity):
            return f"Error: Entity '{entity}' does not exist."
        
        if property not in self.graph.nodes[entity]:
            return f"Error: Property '{property}' does not exist on entity '{entity}'."
        
        del self.graph.nodes[entity][property]
        return f"Property '{property}' removed from entity '{entity}'."

    # ========== Relationship Operations ==========

    def add_relationship(
        self,
        entity1: str,
        relationship: str,
        entity2: str,
        properties: dict = None
    ) -> str:
        """
        Add a directed relationship between two entities with optional properties.
        
        Args:
            entity1: Source entity name
            relationship: Relationship type/label
            entity2: Target entity name
            properties: Optional dictionary of properties for the relationship
        
        Returns:
            str: Success message or error if entities don't exist or relationship exists
        """
        if not self.graph.has_node(entity1):
            return f"Error: Entity '{entity1}' does not exist."
        if not self.graph.has_node(entity2):
            return f"Error: Entity '{entity2}' does not exist."

        # Check if this exact relationship already exists
        if self.graph.has_edge(entity1, entity2):
            existing = self.graph.edges[entity1, entity2]
            if existing.get('relationship') == relationship:
                return (
                    f"Error: Relationship '{entity1} --({relationship})--> {entity2}' "
                    f"already exists."
                )

        props = properties or {}
        props['relationship'] = relationship
        self.graph.add_edge(entity1, entity2, **props)
        return (
            f"Relationship '{entity1} --({relationship})--> {entity2}' "
            f"added successfully."
        )

    def add_relationship_property(
        self,
        entity1: str,
        relationship: str,
        entity2: str,
        property: str,
        value: str
    ) -> str:
        """
        Add or update a property on an existing relationship.
        
        Args:
            entity1: Source entity name
            relationship: Relationship type/label
            entity2: Target entity name
            property: Property name
            value: Property value
        
        Returns:
            str: Success message or error if relationship doesn't exist
        """
        if not self.graph.has_edge(entity1, entity2):
            return (
                f"Error: Relationship '{entity1} --({relationship})--> {entity2}' "
                f"does not exist."
            )
        
        edge_data = self.graph.edges[entity1, entity2]
        if edge_data.get('relationship') != relationship:
            return (
                f"Error: Relationship '{entity1} --({relationship})--> {entity2}' "
                f"does not exist."
            )

        self.graph.edges[entity1, entity2][property] = value
        return (
            f"Property '{property}' set to '{value}' on relationship "
            f"'{entity1} --({relationship})--> {entity2}'"
        )

    def get_relationship(
        self,
        entity1: str,
        relationship: str,
        entity2: str
    ) -> dict | str:
        """
        Retrieve a specific relationship and its properties.
        
        Args:
            entity1: Source entity name
            relationship: Relationship type/label
            entity2: Target entity name
        
        Returns:
            dict: Relationship properties, or error message if not found
        """
        if not self.graph.has_edge(entity1, entity2):
            return (
                f"Error: Relationship '{entity1} --({relationship})--> {entity2}' "
                f"not found."
            )
        
        edge_data = dict(self.graph.edges[entity1, entity2])
        if edge_data.get('relationship') != relationship:
            return (
                f"Error: Relationship '{entity1} --({relationship})--> {entity2}' "
                f"not found."
            )
        
        props = {k: v for k, v in edge_data.items() if k != 'relationship'}
        return {
            "entity1": entity1,
            "relationship": relationship,
            "entity2": entity2,
            "properties": props
        }

    def get_relationships(self, entity: str = None) -> list | str:
        """
        Retrieve relationships, optionally filtered by entity.
        
        Args:
            entity: Optional entity name to filter relationships
        
        Returns:
            list: List of relationship dicts with entity1, type, entity2, and properties
        """
        if entity and not self.graph.has_node(entity):
            return f"Error: Entity '{entity}' does not exist."

        results = []
        for e1, e2, data in self.graph.edges(data=True):
            if entity is None or e1 == entity or e2 == entity:
                props = {k: v for k, v in data.items() if k != 'relationship'}
                results.append({
                    "entity1": e1,
                    "relationship": data.get('relationship', 'unknown'),
                    "entity2": e2,
                    "properties": props
                })

        if entity and not results:
            return f"Error: No relationships found for entity '{entity}'."
        if not results:
            return "Error: No relationships in the graph."
        
        return results

    def remove_relationship(
        self,
        entity1: str,
        relationship: str,
        entity2: str
    ) -> str:
        """
        Remove a relationship between two entities.
        
        Args:
            entity1: Source entity name
            relationship: Relationship type/label
            entity2: Target entity name
        
        Returns:
            str: Success message or error if relationship doesn't exist
        """
        if not self.graph.has_edge(entity1, entity2):
            return (
                f"Error: Relationship '{entity1} --({relationship})--> {entity2}' "
                f"does not exist."
            )
        
        edge_data = self.graph.edges[entity1, entity2]
        if edge_data.get('relationship') != relationship:
            return (
                f"Error: Relationship '{entity1} --({relationship})--> {entity2}' "
                f"does not exist."
            )

        self.graph.remove_edge(entity1, entity2)
        return (
            f"Relationship '{entity1} --({relationship})--> {entity2}' "
            f"removed successfully."
        )

    def remove_relationship_property(
        self,
        entity1: str,
        relationship: str,
        entity2: str,
        property: str
    ) -> str:
        """
        Remove a property from a relationship.
        
        Args:
            entity1: Source entity name
            relationship: Relationship type/label
            entity2: Target entity name
            property: Property name to remove
        
        Returns:
            str: Success message or error if relationship/property doesn't exist
        """
        if not self.graph.has_edge(entity1, entity2):
            return (
                f"Error: Relationship '{entity1} --({relationship})--> {entity2}' "
                f"does not exist."
            )
        
        edge_data = self.graph.edges[entity1, entity2]
        if edge_data.get('relationship') != relationship:
            return (
                f"Error: Relationship '{entity1} --({relationship})--> {entity2}' "
                f"does not exist."
            )
        
        if property not in edge_data or property == 'relationship':
            return (
                f"Error: Property '{property}' does not exist on relationship "
                f"'{entity1} --({relationship})--> {entity2}'."
            )
        
        del self.graph.edges[entity1, entity2][property]
        return (
            f"Property '{property}' removed from relationship "
            f"'{entity1} --({relationship})--> {entity2}'."
        )

    # ========== Query Operations ==========

    def find_entities_by_type(self, entity_type: str) -> List[str]:
        """
        Find all entities of a specific type.
        
        Args:
            entity_type: The type to search for
        
        Returns:
            List of entity names matching the type
        """
        return [
            node for node, data in self.graph.nodes(data=True)
            if data.get('type', '').lower() == entity_type.lower()
        ]

    def find_entities_by_property(
        self, 
        property: str, 
        value: Any = None,
        operator: str = "eq"
    ) -> List[str]:
        """
        Find entities by property value.
        
        Args:
            property: Property name to search
            value: Value to match (None means property exists)
            operator: Comparison operator - "eq", "contains", "gt", "lt", "exists"
        
        Returns:
            List of entity names matching the criteria
        """
        results = []
        for node, data in self.graph.nodes(data=True):
            if property not in data:
                continue
            
            prop_value = data[property]
            
            if operator == "exists":
                results.append(node)
            elif operator == "eq" and prop_value == value:
                results.append(node)
            elif operator == "contains" and value and str(value).lower() in str(prop_value).lower():
                results.append(node)
            elif operator == "gt":
                try:
                    if float(prop_value) > float(value):
                        results.append(node)
                except (ValueError, TypeError):
                    pass
            elif operator == "lt":
                try:
                    if float(prop_value) < float(value):
                        results.append(node)
                except (ValueError, TypeError):
                    pass
        
        return results

    def find_relationships_by_type(self, relationship_type: str) -> List[Dict]:
        """
        Find all relationships of a specific type.
        
        Args:
            relationship_type: The relationship type to search for
        
        Returns:
            List of relationship dicts
        """
        results = []
        for e1, e2, data in self.graph.edges(data=True):
            if data.get('relationship', '').lower() == relationship_type.lower():
                props = {k: v for k, v in data.items() if k != 'relationship'}
                results.append({
                    "entity1": e1,
                    "relationship": data['relationship'],
                    "entity2": e2,
                    "properties": props
                })
        return results

    def get_neighbors(
        self, 
        entity: str, 
        direction: str = "both",
        relationship_type: str = None
    ) -> List[Dict]:
        """
        Get neighboring entities connected to the given entity.
        
        Args:
            entity: The entity to find neighbors for
            direction: "outgoing", "incoming", or "both"
            relationship_type: Optional filter by relationship type
        
        Returns:
            List of dicts with neighbor info and relationship details
        """
        if not self.graph.has_node(entity):
            return []
        
        results = []
        
        if direction in ("outgoing", "both"):
            for _, neighbor, data in self.graph.out_edges(entity, data=True):
                rel_type = data.get('relationship', 'unknown')
                if relationship_type is None or rel_type.lower() == relationship_type.lower():
                    results.append({
                        "entity": neighbor,
                        "direction": "outgoing",
                        "relationship": rel_type,
                        "properties": {k: v for k, v in data.items() if k != 'relationship'}
                    })
        
        if direction in ("incoming", "both"):
            for neighbor, _, data in self.graph.in_edges(entity, data=True):
                rel_type = data.get('relationship', 'unknown')
                if relationship_type is None or rel_type.lower() == relationship_type.lower():
                    results.append({
                        "entity": neighbor,
                        "direction": "incoming",
                        "relationship": rel_type,
                        "properties": {k: v for k, v in data.items() if k != 'relationship'}
                    })
        
        return results

    def find_path(
        self, 
        entity1: str, 
        entity2: str,
        max_depth: int = 10
    ) -> List[str] | str:
        """
        Find the shortest path between two entities.
        
        Args:
            entity1: Starting entity
            entity2: Target entity
            max_depth: Maximum path length to search
        
        Returns:
            List of entity names forming the path, or error message
        """
        if not self.graph.has_node(entity1):
            return f"Error: Entity '{entity1}' does not exist."
        if not self.graph.has_node(entity2):
            return f"Error: Entity '{entity2}' does not exist."
        
        try:
            # Use undirected view for path finding
            undirected = self.graph.to_undirected()
            path = nx.shortest_path(undirected, entity1, entity2)
            if len(path) > max_depth + 1:
                return f"Error: No path found within {max_depth} hops."
            return path
        except nx.NetworkXNoPath:
            return f"Error: No path exists between '{entity1}' and '{entity2}'."

    def find_all_paths(
        self, 
        entity1: str, 
        entity2: str,
        max_depth: int = 5
    ) -> List[List[str]] | str:
        """
        Find all paths between two entities up to a maximum depth.
        
        Args:
            entity1: Starting entity
            entity2: Target entity
            max_depth: Maximum path length
        
        Returns:
            List of paths (each path is a list of entity names), or error message
        """
        if not self.graph.has_node(entity1):
            return f"Error: Entity '{entity1}' does not exist."
        if not self.graph.has_node(entity2):
            return f"Error: Entity '{entity2}' does not exist."
        
        try:
            undirected = self.graph.to_undirected()
            paths = list(nx.all_simple_paths(undirected, entity1, entity2, cutoff=max_depth))
            if not paths:
                return f"Error: No paths found between '{entity1}' and '{entity2}'."
            return paths
        except nx.NetworkXNoPath:
            return f"Error: No path exists between '{entity1}' and '{entity2}'."

    def get_connected_entities(
        self, 
        entity: str, 
        max_depth: int = 2
    ) -> Set[str]:
        """
        Get all entities connected to the given entity within N hops.
        
        Args:
            entity: The starting entity
            max_depth: Maximum number of hops
        
        Returns:
            Set of connected entity names
        """
        if not self.graph.has_node(entity):
            return set()
        
        connected = set()
        undirected = self.graph.to_undirected()
        
        for node in undirected.nodes():
            if node != entity:
                try:
                    path_length = nx.shortest_path_length(undirected, entity, node)
                    if path_length <= max_depth:
                        connected.add(node)
                except nx.NetworkXNoPath:
                    pass
        
        return connected

    def get_subgraph(self, entities: List[str]) -> 'KnowledgeGraph':
        """
        Extract a subgraph containing only the specified entities.
        
        Args:
            entities: List of entity names to include
        
        Returns:
            New KnowledgeGraph containing only the specified entities
        """
        subgraph = KnowledgeGraph()
        subgraph.graph = self.graph.subgraph(entities).copy()
        return subgraph

    # ========== Graph Analytics ==========

    def get_most_connected(self, n: int = 10) -> List[tuple]:
        """
        Get the N most connected entities (by degree centrality).
        
        Args:
            n: Number of entities to return
        
        Returns:
            List of (entity, degree) tuples sorted by degree descending
        """
        degrees = dict(self.graph.degree())
        sorted_degrees = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
        return sorted_degrees[:n]

    def get_isolated_entities(self) -> List[str]:
        """
        Find entities with no relationships.
        
        Returns:
            List of isolated entity names
        """
        return [node for node in self.graph.nodes() if self.graph.degree(node) == 0]

    def is_connected(self) -> bool:
        """
        Check if the graph is fully connected (treating edges as undirected).
        
        Returns:
            True if all entities are reachable from any other entity
        """
        if self.graph.number_of_nodes() == 0:
            return True
        return nx.is_weakly_connected(self.graph)

    def get_connected_components(self) -> List[Set[str]]:
        """
        Get all connected components in the graph.
        
        Returns:
            List of sets, each containing entity names in a connected component
        """
        return [set(c) for c in nx.weakly_connected_components(self.graph)]

    # ========== Persistence ==========

    def to_dict(self) -> Dict:
        """
        Serialize the knowledge graph to a dictionary.
        
        Returns:
            Dictionary representation of the graph
        """
        return {
            "entities": {
                node: dict(data) for node, data in self.graph.nodes(data=True)
            },
            "relationships": [
                {
                    "entity1": e1,
                    "entity2": e2,
                    **data
                }
                for e1, e2, data in self.graph.edges(data=True)
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'KnowledgeGraph':
        """
        Create a knowledge graph from a dictionary.
        
        Args:
            data: Dictionary representation of the graph
        
        Returns:
            New KnowledgeGraph instance
        """
        kg = cls()
        
        for entity, properties in data.get("entities", {}).items():
            kg.graph.add_node(entity, **properties)
        
        for rel in data.get("relationships", []):
            e1 = rel.pop("entity1")
            e2 = rel.pop("entity2")
            kg.graph.add_edge(e1, e2, **rel)
        
        return kg

    def save(self, filepath: str) -> str:
        """
        Save the knowledge graph to a JSON file.
        
        Args:
            filepath: Path to save the file
        
        Returns:
            Success message
        """
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        return f"Knowledge graph saved to {filepath}"

    @classmethod
    def load(cls, filepath: str) -> 'KnowledgeGraph':
        """
        Load a knowledge graph from a JSON file.
        
        Args:
            filepath: Path to the file
        
        Returns:
            New KnowledgeGraph instance
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    # ========== Compatibility Properties ==========

    @property
    def entities(self) -> Dict[str, Dict]:
        """Get all entities and their properties (for backward compatibility)."""
        return {node: dict(data) for node, data in self.graph.nodes(data=True)}

    @property
    def relationships(self) -> Dict[tuple, Dict]:
        """Get all relationships (for backward compatibility)."""
        return {
            (e1, data.get('relationship', 'unknown'), e2): {
                k: v for k, v in data.items() if k != 'relationship'
            }
            for e1, e2, data in self.graph.edges(data=True)
        }

    # ========== String Representation ==========

    def __str__(self) -> str:
        """
        Generate a human-readable string representation of the graph.
        
        Returns:
            str: Formatted representation of entities and relationships
        """
        if self.graph.number_of_nodes() == 0:
            return ""

        kb = "Entities:\n"
        
        for node, data in self.graph.nodes(data=True):
            kb += f"  {node}"
            if data:
                props_str = ", ".join(f"{k}={v}" for k, v in data.items())
                kb += f" ({props_str})"
            kb += "\n"

        if self.graph.number_of_edges() > 0:
            kb += "\nRelationships:\n"
            for e1, e2, data in self.graph.edges(data=True):
                rel_type = data.get('relationship', 'unknown')
                props = {k: v for k, v in data.items() if k != 'relationship'}
                kb += f"  {e1} --({rel_type})--> {e2}"
                if props:
                    props_str = ", ".join(f"{k}={v}" for k, v in props.items())
                    kb += f" [{props_str}]"
                kb += "\n"

        return kb

    def __len__(self) -> int:
        """Return the number of entities in the graph."""
        return self.graph.number_of_nodes()
