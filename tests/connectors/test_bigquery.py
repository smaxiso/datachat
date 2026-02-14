import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.connectors.bigquery import BigQueryConnector
from src.utils.constants import DBType

class TestBigQueryConnector:
    @pytest.fixture
    def connector(self):
        config = {
            'connection_string': 'bigquery://project/dataset',
            'credentials_path': '/path/to/creds.json'
        }
        return BigQueryConnector(config)

    def test_init(self, connector):
        assert connector.project_id == 'project'
        assert connector.dataset_id == 'dataset'
