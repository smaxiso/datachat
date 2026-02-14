import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.connectors.postgresql import PostgreSQLConnector
from src.utils.constants import DBType

class TestPostgreSQLConnector:
    @pytest.fixture
    def connector(self):
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': 'user',
            'password': 'password'
        }
        return PostgreSQLConnector(config)

    def test_init(self, connector):
        assert connector.database == 'testdb'
        assert connector.host == 'localhost'
