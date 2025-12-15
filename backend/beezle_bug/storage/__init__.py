"""
Storage package for database backends.

Provides async storage abstraction with SQLite (and later PostgreSQL) implementations.
"""

from .base import StorageBackend
from .sqlite_backend import SQLiteStorageBackend


async def get_storage_backend(
    backend_type: str = "sqlite",
    **kwargs
) -> StorageBackend:
    """
    Factory function to create and initialize a storage backend.
    
    Args:
        backend_type: Type of backend ("sqlite" or "postgres" in future)
        **kwargs: Backend-specific configuration
            - sqlite: db_path (str) - path to database file
            - postgres: connection_url (str) - PostgreSQL connection URL
    
    Returns:
        Initialized StorageBackend instance
    """
    if backend_type == "sqlite":
        db_path = kwargs.get("db_path", "beezle.db")
        backend = SQLiteStorageBackend(db_path)
        await backend.initialize()
        return backend
    elif backend_type == "postgres":
        raise NotImplementedError("PostgreSQL backend not yet implemented")
    else:
        raise ValueError(f"Unknown storage backend: {backend_type}")


__all__ = [
    "StorageBackend",
    "SQLiteStorageBackend",
    "get_storage_backend",
]






