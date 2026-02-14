import os
import sys
import sys
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import text

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.connectors.factory import ConnectorFactory
from src.connectors.sqlite import SQLiteConnector
from src.connectors.mysql import MySQLConnector
# Postgres requires psycopg2 which might fail in some envs if libpq missing, but we mock it.

class TestConnectorFactory:
    def test_create_sqlite_connector_legacy(self):
        # detailed test for legacy fallback
        with patch.dict(os.environ, {'DB_TYPE': 'sqlite', 'DB_NAME': ':memory:'}):
            # Ensure ACTIVE_SOURCE is not set or points to non-existent to trigger fallback
            with patch.dict(os.environ, {'ACTIVE_SOURCE': 'non_existent_source'}):
                connector = ConnectorFactory.create_connector()
                assert isinstance(connector, SQLiteConnector)
                assert connector.database_path == ':memory:'

    @patch('src.utils.config_loader.ConfigLoader.get_source_config')
    def test_create_mysql_connector_config(self, mock_get_config):
        # Test new config path
        mock_get_config.return_value = {
            'type': 'mysql',
            'config': {
                'host': 'localhost',
                'port': 3306,
                'database': 'testdb',
                'username': 'root',
                'password': ''
            }
        }
        
        with patch.dict(os.environ, {'ACTIVE_SOURCE': 'test_mysql'}):
            connector = ConnectorFactory.create_connector()
            assert isinstance(connector, MySQLConnector)
            assert connector.host == 'localhost'
            assert connector.port == 3306

