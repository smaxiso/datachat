import os
import sys
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from sqlalchemy import text

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.connectors.sqlite import SQLiteConnector

class TestSQLiteConnector:
    @pytest.fixture
    def connector(self):
        config = {'database': ':memory:'}
        conn = SQLiteConnector(config)
        conn.connect()
        # Seed data
        with conn.engine.connect() as connection:
            connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, role TEXT)"))
            connection.execute(text("INSERT INTO users (name, role) VALUES ('Alice', 'Admin')"))
            connection.execute(text("INSERT INTO users (name, role) VALUES ('Bob', 'User')"))
            connection.execute(text("INSERT INTO users (name, role) VALUES ('Charlie', 'User')"))
            connection.commit()
        return conn

    def test_connection(self, connector):
        assert connector.test_connection() is True

    def test_get_schema(self, connector):
        schema = connector.get_schema()
        assert schema.source_type == 'sqlite'
        assert len(schema.tables) == 1
        assert schema.tables[0].name == 'users'
        assert len(schema.tables[0].columns) == 3

    def test_execute_query(self, connector):
        result = connector.execute_query("SELECT * FROM users")
        assert result.success is True
        assert len(result.data) == 3

    def test_get_unique_values(self, connector):
        values = connector.get_unique_values('users', 'role')
        assert len(values) == 2
        assert 'Admin' in values
        assert 'User' in values

    def test_validation_security(self, connector):
        result = connector.validate_query("DROP TABLE users")
        assert result.is_valid is False
        assert "blocked keyword" in result.error_message.lower()
