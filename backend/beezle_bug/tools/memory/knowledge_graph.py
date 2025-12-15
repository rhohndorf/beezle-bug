from pydantic import Field

from beezle_bug.tools import Tool


class AddEntity(Tool):
    """
    Add a new entity to the knowledge graph with optional properties.
    """

    name: str = Field(description="The name of the entity.")
    type: str = Field(description="The type of the entity (e.g. Person, City, Company, etc).")

    async def run(self, agent):
        entity = {"name": self.name, "type": self.type}
        return await agent.knowledge_graph.add_entity(self.name, entity)


class AddPropertyToEntity(Tool):
    """
    Add a new property to an existing entity in the knowledge graph.
    """

    entity: str = Field(description="The name of the entity")
    property: str = Field(description="The property name")
    value: str = Field(description="The property value")

    async def run(self, agent):
        return await agent.knowledge_graph.add_entity_property(self.entity, self.property, self.value)


class AddRelationship(Tool):
    """
    Add a new relationship between two entities in the knowledge graph.
    """

    entity1: str = Field(..., description="The starting entity of the relationship.")
    relationship: str = Field(..., description="The type of relationship.")
    entity2: str = Field(..., description="The target entity of the relationship.")

    async def run(self, agent):
        return await agent.knowledge_graph.add_relationship(self.entity1, self.relationship, self.entity2)


class GetEntity(Tool):
    """
    Retrieve an entity from the knowledge graph.
    """

    entity: str = Field(None, description="The entity to retrieve")

    async def run(self, agent):
        # get_entity is sync (operates on in-memory graph)
        return agent.knowledge_graph.get_entity(self.entity)


class GetRelationships(Tool):
    """
    Retrieve relationships involving a specific entity, or all relationships if no entity is specified.
    """

    entity: str = Field(
        None, description="The entity whose relationships to retrieve. If None, retrieves all relationships."
    )

    async def run(self, agent):
        # get_relationships is sync (operates on in-memory graph)
        return agent.knowledge_graph.get_relationships(self.entity)


class RemoveRelationship(Tool):
    """
    Remove a relationship between two entities from the knowledge graph.
    Use this when information has changed (e.g., someone moved, changed jobs).
    """

    entity1: str = Field(..., description="The starting entity of the relationship to remove.")
    relationship: str = Field(..., description="The type of relationship to remove.")
    entity2: str = Field(..., description="The target entity of the relationship to remove.")

    async def run(self, agent):
        return await agent.knowledge_graph.remove_relationship(self.entity1, self.relationship, self.entity2)


class RemoveEntity(Tool):
    """
    Remove an entity and all its relationships from the knowledge graph.
    Use with caution - this will also remove all relationships involving this entity.
    """

    entity: str = Field(..., description="The name of the entity to remove.")

    async def run(self, agent):
        return await agent.knowledge_graph.remove_entity(self.entity)


class RemoveEntityProperty(Tool):
    """
    Remove a specific property from an entity in the knowledge graph.
    Use when a property is no longer valid or needs to be cleared before updating.
    """

    entity: str = Field(..., description="The name of the entity.")
    property: str = Field(..., description="The property name to remove.")

    async def run(self, agent):
        return await agent.knowledge_graph.remove_entity_property(self.entity, self.property)


class AddPropertyToRelationship(Tool):
    """
    Add a property to an existing relationship in the knowledge graph.
    Use this for relationship metadata like start_date, end_date, confidence, source, etc.
    """

    entity1: str = Field(..., description="The starting entity of the relationship.")
    relationship: str = Field(..., description="The type of relationship.")
    entity2: str = Field(..., description="The target entity of the relationship.")
    property: str = Field(..., description="The property name to add.")
    value: str = Field(..., description="The property value.")

    async def run(self, agent):
        return await agent.knowledge_graph.add_relationship_property(
            self.entity1, self.relationship, self.entity2, self.property, self.value
        )


class GetRelationship(Tool):
    """
    Retrieve a specific relationship and its properties from the knowledge graph.
    """

    entity1: str = Field(..., description="The starting entity of the relationship.")
    relationship: str = Field(..., description="The type of relationship.")
    entity2: str = Field(..., description="The target entity of the relationship.")

    async def run(self, agent):
        # get_relationship is sync (operates on in-memory graph)
        return agent.knowledge_graph.get_relationship(self.entity1, self.relationship, self.entity2)


class RemoveRelationshipProperty(Tool):
    """
    Remove a specific property from a relationship in the knowledge graph.
    """

    entity1: str = Field(..., description="The starting entity of the relationship.")
    relationship: str = Field(..., description="The type of relationship.")
    entity2: str = Field(..., description="The target entity of the relationship.")
    property: str = Field(..., description="The property name to remove.")

    async def run(self, agent):
        return await agent.knowledge_graph.remove_relationship_property(
            self.entity1, self.relationship, self.entity2, self.property
        )


# ========== Query Tools (sync - operate on in-memory graph) ==========

class FindEntitiesByType(Tool):
    """
    Find all entities of a specific type in the knowledge graph.
    Use this to discover all entities of a category (e.g., all people, all cities).
    """

    entity_type: str = Field(..., description="The type to search for (e.g., 'person', 'city', 'organization').")

    async def run(self, agent):
        results = agent.knowledge_graph.find_entities_by_type(self.entity_type)
        if not results:
            return f"No entities of type '{self.entity_type}' found."
        return results


class FindEntitiesByProperty(Tool):
    """
    Find entities that have a specific property value.
    Use this to search for entities matching certain criteria.
    """

    property: str = Field(..., description="The property name to search.")
    value: str = Field(None, description="The value to match. If None, finds entities where property exists.")
    operator: str = Field(
        default="eq",
        description="Comparison operator: 'eq' (equals), 'contains' (substring), 'gt' (greater than), 'lt' (less than), 'exists' (property exists)."
    )

    async def run(self, agent):
        results = agent.knowledge_graph.find_entities_by_property(
            self.property, self.value, self.operator
        )
        if not results:
            return f"No entities found with property '{self.property}' matching criteria."
        return results


class FindRelationshipsByType(Tool):
    """
    Find all relationships of a specific type in the knowledge graph.
    Use this to discover all connections of a certain kind (e.g., all 'works_at' relationships).
    """

    relationship_type: str = Field(..., description="The relationship type to search for (e.g., 'lives_in', 'works_at').")

    async def run(self, agent):
        results = agent.knowledge_graph.find_relationships_by_type(self.relationship_type)
        if not results:
            return f"No relationships of type '{self.relationship_type}' found."
        return results


class GetNeighbors(Tool):
    """
    Get all entities directly connected to a given entity.
    Use this to explore what an entity is connected to.
    """

    entity: str = Field(..., description="The entity to find neighbors for.")
    direction: str = Field(
        default="both",
        description="Direction of relationships: 'outgoing', 'incoming', or 'both'."
    )
    relationship_type: str = Field(
        None,
        description="Optional: filter by relationship type."
    )

    async def run(self, agent):
        results = agent.knowledge_graph.get_neighbors(
            self.entity, self.direction, self.relationship_type
        )
        if not results:
            return f"No neighbors found for entity '{self.entity}'."
        return results


class FindPath(Tool):
    """
    Find the shortest path between two entities in the knowledge graph.
    Use this to discover how two entities are connected.
    """

    entity1: str = Field(..., description="The starting entity.")
    entity2: str = Field(..., description="The target entity.")
    max_depth: int = Field(default=10, description="Maximum path length to search.")

    async def run(self, agent):
        return agent.knowledge_graph.find_path(self.entity1, self.entity2, self.max_depth)


class GetConnectedEntities(Tool):
    """
    Get all entities connected to a given entity within N hops.
    Use this to explore the neighborhood of an entity.
    """

    entity: str = Field(..., description="The starting entity.")
    max_depth: int = Field(default=2, description="Maximum number of hops (1-5 recommended).")

    async def run(self, agent):
        results = agent.knowledge_graph.get_connected_entities(self.entity, self.max_depth)
        if not results:
            return f"No connected entities found for '{self.entity}'."
        return list(results)


class GetMostConnected(Tool):
    """
    Get the most connected entities in the knowledge graph.
    Use this to find the most important/central entities.
    """

    n: int = Field(default=10, description="Number of entities to return.")

    async def run(self, agent):
        results = agent.knowledge_graph.get_most_connected(self.n)
        if not results:
            return "The knowledge graph is empty."
        return [{"entity": entity, "connections": degree} for entity, degree in results]


class GetIsolatedEntities(Tool):
    """
    Find entities with no relationships in the knowledge graph.
    Use this to find orphaned entities that might need connections.
    """

    async def run(self, agent):
        results = agent.knowledge_graph.get_isolated_entities()
        if not results:
            return "No isolated entities found. All entities are connected."
        return results


class CheckGraphConnectivity(Tool):
    """
    Check if the knowledge graph is fully connected.
    Use this to verify graph integrity and find disconnected subgraphs.
    """

    async def run(self, agent):
        is_connected = agent.knowledge_graph.is_connected()
        if is_connected:
            return "The knowledge graph is fully connected."
        
        components = agent.knowledge_graph.get_connected_components()
        return {
            "is_connected": False,
            "num_components": len(components),
            "components": [list(c) for c in components]
        }
