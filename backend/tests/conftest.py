"""
Test configuration and fixtures
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Mock database dependencies to avoid connection issues during testing
@pytest.fixture(autouse=True)
def mock_database():
    """Mock database dependencies for all tests"""
    import sys
    from unittest.mock import MagicMock
    
    # Mock SQLAlchemy components
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.rollback = AsyncMock()
    
    # Mock database functions
    async def mock_get_db():
        yield mock_session
    
    # Replace imports
    if 'app.core.database' in sys.modules:
        sys.modules['app.core.database'].get_db = mock_get_db
    
    return mock_session

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)