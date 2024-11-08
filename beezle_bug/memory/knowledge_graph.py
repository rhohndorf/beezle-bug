class KnowledgeGraph:
    def __init__(self):
        # Use sets for unique entities and relationships
        self.entities = {}
        self.relationships = set()

    def add_entity(self, entity, properties):
        """Add a new entity with optional properties. Returns success or error message."""

        # Check if entity already exists
        if entity in self.entities:
            return f"Error: Entity '{entity}' already exists."

        # Add the entity to the set and store its properties in a separate dictionary
        self.entities[entity] = properties
        return f"Entity '{entity}' added successfully."

    def add_entity_property(self, entity, property, value):
        if entity not in self.entities.keys():
            return f"Error: Entity '{entity}' does not exist."

        self.entities[entity][property] = value

        return f"Property {property} set to {value} on entity {entity}"

    def add_relationship(self, entity1, relationship, entity2):
        """Add a directed relationship between two entities. Returns success or error message."""
        # Check if both entities exist
        if entity1 not in self.entities.keys():
            return f"Error: Entity '{entity1}' does not exist."
        if entity2 not in self.entities.keys():
            return f"Error: Entity '{entity2}' does not exist."

        # Add the relationship as a tuple and check for duplicates
        relationship_tuple = (entity1, relationship, entity2)
        if relationship_tuple in self.relationships:
            return f"Error: Relationship '{entity1} --({relationship})--> {entity2}' already exists."

        self.relationships.add(relationship_tuple)
        return f"Relationship '{entity1} --({relationship})--> {entity2}' added successfully."

    def get_entity(self, entity):
        """Retrieve the properties of an entity or return an error message if not found."""
        if entity not in self.entities.keys():
            return f"Error: Entity '{entity}' not found."
        return self.entities.get(entity, {})

    def get_relationships(self, entity=None):
        """Retrieve relationships, optionally filtered by a specific entity."""
        if entity and entity not in self.entities:
            return f"Error: Entity '{entity}' does not exist."

        if entity:
            # Filter relationships to those involving the specified entity
            filtered_relationships = {rel for rel in self.relationships if rel[0] == entity or rel[2] == entity}
            if not filtered_relationships:
                return f"Error: No relationships found for entity '{entity}'."
            return filtered_relationships

        # Return all relationships if no specific entity is provided
        return self.relationships if self.relationships else "Error: No relationships in the graph."

    def __str__(self) -> str:
        """Display entities and relationships."""

        if len(self.entities) == 0:
            return ""

        kb = ""
        kb += "Entities:\n"
        for entity, properties in self.entities.items():
            for property, value in properties.items():
                kb += f"{entity} {property} {value} \n"

        if self.relationships:
            kb += "\nRelationships:\n"

            for entity1, relationship, entity2 in self.relationships:
                kb += f"{entity1} --({relationship})--> {entity2}\n"

        return kb
