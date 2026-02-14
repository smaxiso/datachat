import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.connectors.dynamodb import DynamoDBConnector

class TestDynamoDBConnector:
    @pytest.fixture
    def connector(self):
        config = {
            'region_name': 'us-east-1',
            'aws_access_key_id': 'test',
            'aws_secret_access_key': 'test'
        }
        return DynamoDBConnector(config)

    @patch('src.connectors.dynamodb.boto3.Session')
    def test_connect_success(self, mock_session, connector):
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        
        assert connector.connect() is True
        mock_session.assert_called_once()
        mock_client.list_tables.assert_called_once()

    @patch('src.connectors.dynamodb.boto3.Session')
    def test_get_schema(self, mock_session, connector):
        mock_client = MagicMock()
        mock_resource = MagicMock()
        mock_table = MagicMock()
        
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.resource.return_value = mock_resource
        
        # Mock list_tables
        paginator = MagicMock()
        paginator.paginate.return_value = [{'TableNames': ['users']}]
        mock_client.get_paginator.return_value = paginator
        
        # Mock resource table
        mock_resource.Table.return_value = mock_table
        mock_table.key_schema = [{'AttributeName': 'id', 'KeyType': 'HASH'}]
        mock_table.scan.return_value = {'Items': [], 'Count': 100}
        mock_table.item_count = 100

        connector.connect()
        schema = connector.get_schema()
        
        assert schema.source_type == 'dynamodb'
        assert len(schema.tables) == 1
        assert schema.tables[0].name == 'users'
        assert schema.tables[0].columns[0].name == 'id'
