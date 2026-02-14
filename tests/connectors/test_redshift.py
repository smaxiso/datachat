import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.connectors.redshift import RedshiftConnector

class TestRedshiftConnector:
    @pytest.fixture
    def connector(self):
        config = {
            'host': 'redshift-cluster',
            'port': 5439,
            'database': 'dev',
            'username': 'admin',
            'password': 'password'
        }
        return RedshiftConnector(config)

    @patch('src.connectors.redshift.create_engine')
    def test_connect_success(self, mock_create_engine, connector):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        
        assert connector.connect() is True
        
        args, kwargs = mock_create_engine.call_args
        assert "redshift+psycopg2://admin:password@redshift-cluster:5439/dev" in args[0]

    @patch('src.connectors.redshift.create_engine')
    def test_get_schema(self, mock_create_engine, connector):
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        connector.engine = mock_engine
        
        with patch('src.connectors.redshift.inspect') as mock_inspect:
            mock_inspector = MagicMock()
            mock_inspect.return_value = mock_inspector
            mock_inspector.get_table_names.return_value = ['sales']
            mock_inspector.get_columns.return_value = [{'name': 'id', 'type': 'INTEGER', 'nullable': False}]
            
            schema = connector.get_schema()
            assert schema.source_type == 'redshift'
            assert schema.tables[0].name == 'sales'
