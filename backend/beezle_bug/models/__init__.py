"""
SQLModel database models for Beezle Bug.

These models map directly to database tables and provide ORM functionality.
"""

from .project import ProjectDB
from .node import NodeDB
from .edge import EdgeDB

__all__ = [
    "ProjectDB",
    "NodeDB", 
    "EdgeDB",
]

