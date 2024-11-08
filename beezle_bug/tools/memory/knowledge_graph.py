import logging

from pydantic import Field

from beezle_bug.tools import Tool


class AddEntity(Tool):
    """
    Add a new entity to the knowledge graph with optional properties.
    """

    name: str = Field(description="The name of the entity.")
    type: str = Field(description="The type of the entity (e.g. Person, City, Company, etc).")
    # properties: dict = Field(default_factory=dict, description="Optional properties for the entity.")

    def run(self, agent):
        # Directly use agent's knowledge graph and return the result
        entity = {"name": self.name, "type": self.type}
        return agent.knowledge_graph.add_entity(self.name, entity)


class AddPropertyToEntity(Tool):
    """
    Add a new property to an existing entity in the knowledge graph.
    """

    entity: str = Field(description="The name of the entity")
    property: str = Field(description="The property name")
    value: str = Field(description="The property value")

    def run(self, agent):
        # Directly use agent's knowledge graph and return the result
        return agent.knowledge_graph.add_entity_property(self.entity, self.property, self.value)


class AddRelationship(Tool):
    """
    Add a new relationship between two entities in the knowledge graph.
    """

    entity1: str = Field(..., description="The starting entity of the relationship.")
    relationship: str = Field(..., description="The type of relationship.")
    entity2: str = Field(..., description="The target entity of the relationship.")

    def run(self, agent):
        # Directly use agent's knowledge graph and return the result
        return agent.knowledge_graph.add_relationship(self.entity1, self.relationship, self.entity2)


# class UpdateEntityPropertiesInKnowledgeGraph(Tool):
#     """
#     Update properties for an existing entity in the knowledge graph.
#     """

#     entity: str = Field(..., description="The entity whose properties will be updated.")
#     properties: dict = Field(..., description="New properties to add or update for the entity.")

#     def run(self, agent):
#         # Directly use agent's knowledge graph and return the result
#         return agent.knowledge_graph.update_entity_properties(self.entity, self.properties)


class GetEntity(Tool):
    """
    Retrieve an entity from the knowledge graph.
    """

    entity: str = Field(None, description="The entity to retrieve")

    def run(self, agent):
        # Directly use agent's knowledge graph and return the result
        return agent.knowledge_graph.get_entity(self.entity)


class GetRelationships(Tool):
    """
    Retrieve relationships involving a specific entity, or all relationships if no entity is specified.
    """

    entity: str = Field(
        None, description="The entity whose relationships to retrieve. If None, retrieves all relationships."
    )

    def run(self, agent):
        # Directly use agent's knowledge graph and return the result
        return agent.knowledge_graph.get_relationships(self.entity)
