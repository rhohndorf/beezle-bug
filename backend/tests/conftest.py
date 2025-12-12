"""
Pytest configuration and fixtures.
"""

import pytest


# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
def anyio_backend():
    return 'asyncio'






