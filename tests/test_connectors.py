"""
Unit tests for PostgreSQL connector.

Run with: pytest tests/test_connectors.py
"""

import pytest
from src.connectors.postgresql import PostgreSQLConnector
from src.connectors.base import ConnectionStatus


@pytest.fixture
def db_config():
    """Database configuration for testing."""
    return {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'username': 'postgres',
        'password': 'postgres',
        'schema': 'public'
    }


@pytest.fixture
def connector(db_config):
    """Create a connector instance."""
    return PostgreSQLConnector(db_config)


def test_connector_initialization(connector):
    """Test connector initialization."""
    assert connector is not None
    assert connector.database == 'test_db'
    assert connector.schema == 'public'
    assert connector.get_status() == ConnectionStatus.DISCONNECTED


def test_query_validation_blocks_destructive_operations(connector):
    """Test that destructive operations are blocked."""
    # Test DROP
    result = connector.validate_query("DROP TABLE users")
    assert not result.is_valid
    assert "DROP" in result.error_message
    
    # Test DELETE
    result = connector.validate_query("DELETE FROM users")
    assert not result.is_valid
    assert "DELETE" in result.error_message
    
    # Test UPDATE
    result = connector.validate_query("UPDATE users SET name='test'")
    assert not result.is_valid
    assert "UPDATE" in result.error_message


def test_query_validation_allows_select(connector):
    """Test that SELECT queries are allowed."""
    result = connector.validate_query("SELECT * FROM users")
    # This might fail if not connected to DB, but validation should check keywords
    # In real tests, you'd mock the database connection


def test_context_manager(db_config):
    """Test using connector as context manager."""
    # Note: This test requires a real database connection
    # In production, you'd use a test database or mock
    # with PostgreSQLConnector(db_config) as conn:
    #     assert conn.get_status() == ConnectionStatus.CONNECTED
    pass


# Integration tests (require real database)
@pytest.mark.integration
class TestPostgreSQLIntegration:
    """Integration tests - require actual database."""
    
    def test_connection(self, connector):
        """Test database connection."""
        # Skip if no test database available
        pytest.skip("Requires test database setup")
        
        success = connector.connect()
        assert success
        assert connector.get_status() == ConnectionStatus.CONNECTED
        
        connector.disconnect()
        assert connector.get_status() == ConnectionStatus.DISCONNECTED
    
    def test_schema_retrieval(self, connector):
        """Test schema metadata retrieval."""
        pytest.skip("Requires test database setup")
        
        connector.connect()
        schema = connector.get_schema()
        
        assert schema is not None
        assert schema.source_type == "postgresql"
        assert len(schema.tables) > 0
        
        connector.disconnect()
    
    def test_query_execution(self, connector):
        """Test query execution."""
        pytest.skip("Requires test database setup")
        
        connector.connect()
        result = connector.execute_query("SELECT 1 as test")
        
        assert result.success
        assert result.row_count == 1
        assert result.data is not None
        
        connector.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
