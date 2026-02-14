import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.connectors.mysql import MySQLConnector

class TestMySQLConnector:
    @pytest.fixture
    def connector(self):
        config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'testdb',
            'username': 'root',
            'password': 'password'
        }
        return MySQLConnector(config)

    @patch('src.connectors.mysql.create_engine')
    def test_connect_success(self, mock_create_engine, connector):
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        assert connector.connect() is True
        mock_create_engine.assert_called_once()
        # Verify connection string format
        args, _ = mock_create_engine.call_args
        assert "mysql+pymysql://root:password@localhost:3306/testdb" in args[0]

    @patch('src.connectors.mysql.create_engine')
    def test_get_schema(self, mock_create_engine, connector):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        connector.engine = mock_engine
        
        # Mock inspector
        with patch('src.connectors.mysql.inspect') as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspect.return_value = mock_inspector
            
            mock_inspector.get_table_names.return_value = ['users']
            mock_inspector.get_columns.return_value = [
                {'name': 'id', 'type': 'INTEGER', 'nullable': False},
                {'name': 'username', 'type': 'VARCHAR', 'nullable': True}
            ]
            
            # Mock row count query
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_result = MagicMock()
            mock_result.scalar.return_value = 100
            mock_conn.execute.return_value = mock_result
            
            schema = connector.get_schema()
            
            assert schema.source_type == 'mysql'
            assert len(schema.tables) == 1
            assert schema.tables[0].name == 'users'
            assert schema.tables[0].row_count == 100
