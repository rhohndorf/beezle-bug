"""
Entity type schemas for the knowledge graph.

Defines expected properties and common relationships for different entity types.
This provides guidance to agents about what information to extract and helps
the UI show entity completeness.
"""

from typing import Dict, List, Any, Optional


ENTITY_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "person": {
        "description": "An individual human being",
        "properties": {
            "first_name": {"type": "string", "description": "First/given name"},
            "last_name": {"type": "string", "description": "Family/surname"},
            "birth_year": {"type": "integer", "description": "Year of birth"},
            "birth_month": {"type": "string", "description": "Month of birth (e.g., 'March')"},
            "birth_day": {"type": "integer", "description": "Day of birth (1-31)"},
            "gender": {"type": "string", "description": "Gender identity"},
            "occupation": {"type": "string", "description": "Primary profession or role"},
        },
        "common_relationships": [
            "lives_in",
            "born_in",
            "works_at",
            "studied_at",
            "knows",
            "married_to",
            "friends_with",
            "parent_of",
            "child_of",
            "sibling_of",
        ]
    },
    "organization": {
        "description": "A company, institution, or organized group",
        "properties": {
            "founded_year": {"type": "integer", "description": "Year the organization was founded"},
            "industry": {"type": "string", "description": "Primary industry or sector"},
            "description": {"type": "string", "description": "Brief description of what the organization does"},
            "website": {"type": "string", "description": "Official website URL"},
        },
        "common_relationships": [
            "headquartered_in",
            "founded_by",
            "part_of",
            "subsidiary_of",
            "competitor_of",
        ]
    },
    "city": {
        "description": "A city or town",
        "properties": {
            "population": {"type": "integer", "description": "Approximate population"},
            "founded_year": {"type": "integer", "description": "Year the city was founded"},
            "timezone": {"type": "string", "description": "Primary timezone"},
        },
        "common_relationships": [
            "located_in",
            "capital_of",
            "part_of",
        ]
    },
    "country": {
        "description": "A sovereign nation",
        "properties": {
            "population": {"type": "integer", "description": "Approximate population"},
            "official_language": {"type": "string", "description": "Primary official language"},
            "currency": {"type": "string", "description": "Official currency"},
            "government_type": {"type": "string", "description": "Type of government"},
        },
        "common_relationships": [
            "part_of",
            "borders",
            "member_of",
        ]
    },
    "region": {
        "description": "A state, province, or geographic area",
        "properties": {
            "population": {"type": "integer", "description": "Approximate population"},
            "area_km2": {"type": "number", "description": "Area in square kilometers"},
        },
        "common_relationships": [
            "located_in",
            "part_of",
            "capital_is",
        ]
    },
    "product": {
        "description": "A software application, physical product, or service",
        "properties": {
            "created_year": {"type": "integer", "description": "Year the product was created/released"},
            "version": {"type": "string", "description": "Current version"},
            "description": {"type": "string", "description": "Brief description of the product"},
            "license": {"type": "string", "description": "License type (for software)"},
        },
        "common_relationships": [
            "created_by",
            "owned_by",
            "part_of",
            "competes_with",
        ]
    },
    "programming_language": {
        "description": "A programming or scripting language",
        "properties": {
            "created_year": {"type": "integer", "description": "Year the language was created"},
            "paradigm": {"type": "string", "description": "Programming paradigm (e.g., 'object-oriented')"},
            "typing": {"type": "string", "description": "Type system (e.g., 'static', 'dynamic')"},
        },
        "common_relationships": [
            "created_by",
            "influenced_by",
            "influenced",
        ]
    },
    "event": {
        "description": "A meeting, conference, occurrence, or historical event",
        "properties": {
            "date": {"type": "string", "description": "Date of the event (YYYY-MM-DD)"},
            "year": {"type": "integer", "description": "Year of the event"},
            "description": {"type": "string", "description": "Brief description of the event"},
        },
        "common_relationships": [
            "occurred_in",
            "organized_by",
            "attended_by",
            "part_of",
        ]
    },
    "landmark": {
        "description": "A notable building, monument, or geographic feature",
        "properties": {
            "built_year": {"type": "integer", "description": "Year built/constructed"},
            "height_meters": {"type": "number", "description": "Height in meters"},
            "description": {"type": "string", "description": "Brief description"},
        },
        "common_relationships": [
            "located_in",
            "built_by",
            "owned_by",
        ]
    },
    "concept": {
        "description": "An abstract idea, topic, or field of study",
        "properties": {
            "description": {"type": "string", "description": "Brief description of the concept"},
            "field": {"type": "string", "description": "Related field or domain"},
        },
        "common_relationships": [
            "part_of",
            "related_to",
            "originated_from",
        ]
    },
}


def get_schema(entity_type: str) -> Optional[Dict[str, Any]]:
    """
    Get the schema for an entity type.
    
    Args:
        entity_type: The type of entity (e.g., 'person', 'organization')
        
    Returns:
        Schema dictionary or None if type is not defined
    """
    return ENTITY_SCHEMAS.get(entity_type.lower())


def get_expected_properties(entity_type: str) -> List[str]:
    """
    Get list of expected property names for an entity type.
    
    Args:
        entity_type: The type of entity
        
    Returns:
        List of property names
    """
    schema = get_schema(entity_type)
    if schema:
        return list(schema.get("properties", {}).keys())
    return []


def get_missing_properties(entity_type: str, current_properties: Dict[str, Any]) -> List[str]:
    """
    Get list of expected properties that are not yet filled for an entity.
    
    Args:
        entity_type: The type of entity
        current_properties: Dictionary of currently set properties
        
    Returns:
        List of property names that are expected but not set
    """
    expected = set(get_expected_properties(entity_type))
    current = set(current_properties.keys())
    return sorted(list(expected - current))


def get_common_relationships(entity_type: str) -> List[str]:
    """
    Get list of common relationship types for an entity type.
    
    Args:
        entity_type: The type of entity
        
    Returns:
        List of relationship type names
    """
    schema = get_schema(entity_type)
    if schema:
        return schema.get("common_relationships", [])
    return []


def get_entity_completeness(entity_type: str, current_properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate how complete an entity is based on its schema.
    
    Args:
        entity_type: The type of entity
        current_properties: Dictionary of currently set properties
        
    Returns:
        Dictionary with completeness information
    """
    expected = get_expected_properties(entity_type)
    if not expected:
        return {
            "has_schema": False,
            "filled": len(current_properties),
            "expected": 0,
            "percentage": 100,
            "missing": []
        }
    
    missing = get_missing_properties(entity_type, current_properties)
    filled = len(expected) - len(missing)
    
    return {
        "has_schema": True,
        "filled": filled,
        "expected": len(expected),
        "percentage": round((filled / len(expected)) * 100),
        "missing": missing
    }


def get_all_entity_types() -> List[str]:
    """Get list of all defined entity types."""
    return list(ENTITY_SCHEMAS.keys())


def get_schema_for_prompt() -> str:
    """
    Generate a compact schema description for inclusion in system prompts.
    
    Returns:
        Formatted string describing all entity schemas
    """
    lines = []
    
    for entity_type, schema in ENTITY_SCHEMAS.items():
        props = list(schema.get("properties", {}).keys())
        rels = schema.get("common_relationships", [])
        
        props_str = ", ".join(props) if props else "none defined"
        rels_str = ", ".join(rels[:5])  # Limit to first 5 relationships
        if len(rels) > 5:
            rels_str += ", ..."
            
        lines.append(f"- **{entity_type}**: [{props_str}] | relationships: [{rels_str}]")
    
    return "\n".join(lines)


def get_detailed_schema_for_prompt() -> str:
    """
    Generate a more detailed schema description for prompts that need it.
    
    Returns:
        Detailed formatted string describing all entity schemas
    """
    lines = []
    
    for entity_type, schema in ENTITY_SCHEMAS.items():
        lines.append(f"### {entity_type.title()}")
        lines.append(f"{schema.get('description', '')}")
        lines.append("")
        
        props = schema.get("properties", {})
        if props:
            lines.append("Properties:")
            for prop_name, prop_info in props.items():
                lines.append(f"  - {prop_name}: {prop_info.get('description', '')}")
        
        rels = schema.get("common_relationships", [])
        if rels:
            lines.append(f"Common relationships: {', '.join(rels)}")
        
        lines.append("")
    
    return "\n".join(lines)




