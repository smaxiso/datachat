"""
DynamoDB data source connector implementation.

This module provides a concrete implementation of the BaseConnector for AWS DynamoDB.
It uses PartiQL to support SQL-like querying.
"""

import boto3
from typing import List, Dict, Any, Optional
import pandas as pd
from loguru import logger
import time

from src.connectors.base import (
    BaseConnector,
    SchemaMetadata,
    TableMetadata,
    ColumnMetadata,
    QueryResult,
    ValidationResult,
    ConnectionStatus
)
from src.utils.constants import DynamoDBConstants


class DynamoDBConnector(BaseConnector):
    """AWS DynamoDB connector."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize DynamoDB connector.
        
        Args:
            config: Configuration dictionary with keys:
                - region_name: AWS region
                - aws_access_key_id: AWS access key (optional if using env vars or profile)
                - aws_secret_access_key: AWS secret key (optional)
                - table_name: Specific table to query (if focusing on one) or list of tables?
                  Actually, usually we explore tables in the account/region.
        """
        super().__init__(config)
        self.region_name = config.get('region_name', 'us-east-1')
        self.aws_access_key_id = config.get('aws_access_key_id')
        self.aws_secret_access_key = config.get('aws_secret_access_key')
        self.client = None
        self.resource = None
        
    def connect(self) -> bool:
        """Establish connection to DynamoDB."""
        try:
            session_args = {'region_name': self.region_name}
            if self.aws_access_key_id and self.aws_secret_access_key:
                session_args['aws_access_key_id'] = self.aws_access_key_id
                session_args['aws_secret_access_key'] = self.aws_secret_access_key
                
            session = boto3.Session(**session_args)
            self.client = session.client('dynamodb')
            self.resource = session.resource('dynamodb')
            
            # Test connection by listing tables
            self.client.list_tables(Limit=1)
            
            self._status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to DynamoDB in region {self.region_name}")
            return True
        except Exception as e:
            self._status = ConnectionStatus.ERROR
            logger.error(f"Failed to connect to DynamoDB: {e}")
            return False

    def disconnect(self) -> bool:
        """Close the connection."""
        self.client = None
        self.resource = None
        self._status = ConnectionStatus.DISCONNECTED
        return True
    
    def test_connection(self) -> bool:
        try:
            self.client.list_tables(Limit=1)
            return True
        except Exception:
            return False

    def get_schema(self) -> SchemaMetadata:
        """Retrieve schema metadata by scanning tables."""
        if not self.client:
             raise RuntimeError("Database not connected")
             
        tables = []
        paginator = self.client.get_paginator('list_tables')
        
        try:
            for page in paginator.paginate():
                for table_name in page['TableNames']:
                    table = self.resource.Table(table_name)
                    
                    # Infer columns from a small scan
                    # Note: This is expensive if we scan too much. Just grabbing 1 item or 5.
                    # DynamoDB doesn't have a fixed schema except PK.
                    scan_result = table.scan(Limit=5)
                    items = scan_result.get('Items', [])
                    
                    columns = []
                    # Get Keys
                    for key_schema in table.key_schema:
                        columns.append(ColumnMetadata(
                            name=key_schema['AttributeName'],
                            data_type='KEY', # Type is in AttributeDefinitions but let's genericize
                            nullable=False,
                            primary_key=True
                        ))
                    
                    # Infer other attributes
                    attributes = set()
                    for item in items:
                        attributes.update(item.keys())
                    
                    existing_cols = {c.name for c in columns}
                    for attr in attributes:
                        if attr not in existing_cols:
                            # Simple type inference based on first non-null value?
                            # For now, just string.
                            columns.append(ColumnMetadata(
                                name=attr,
                                data_type='ANY',
                                nullable=True
                            ))
                            
                    tables.append(TableMetadata(
                        name=table_name,
                        schema='default',
                        columns=columns,
                        row_count=table.item_count # Approximate
                    ))
                    
            return SchemaMetadata(
                source_name=f"dynamodb-{self.region_name}",
                source_type="dynamodb",
                tables=tables,
                relationships=[]
            )
        except Exception as e:
             logger.error(f"Error getting schema: {e}")
             return SchemaMetadata(source_name="error", source_type="dynamodb", tables=[], relationships=[])

    def execute_query(self, sql: str, params: Optional[Dict] = None, timeout: int = 30) -> QueryResult:
        """Execute PartiQL statement."""
        # Simple PartiQL validation?
        # "SELECT * FROM TableName WHERE ..."
        
        try:
            start_time = time.time()
            
            # PartiQL execution
            # Note: params handling in boto3 is specific, standard SQL params replacement might need adaptation.
            # For now, assuming SQL string is fully formed or handles basic quoting.
            
            # Remove trailing semicolon if present
            sql_clean = sql.strip().rstrip(';')
            
            response = self.client.execute_statement(Statement=sql_clean)
            
            items = []
            if 'Items' in response:
                # Need to deserialize DynamoDB JSON format: {'S': 'val'} -> 'val'
                deserializer = boto3.dynamodb.types.TypeDeserializer()
                for item in response['Items']:
                    python_item = {k: deserializer.deserialize(v) for k, v in item.items()}
                    items.append(python_item)
            
            df = pd.DataFrame(items)
            execution_time = time.time() - start_time
            
            return QueryResult(
                success=True,
                data=df,
                row_count=len(df),
                execution_time=execution_time,
                sql_executed=sql
            )
            
        except Exception as e:
            return QueryResult(success=False, error_message=str(e), sql_executed=sql)

    def validate_query(self, sql: str) -> ValidationResult:
        """
        Validate PartiQL query for DynamoDB limitations.
        Blocks complex operations that are not efficiently supported.
        """
        sql_upper = sql.upper()
        
        # 1. Block destructive operations
        for k in DynamoDBConstants.BLOCKED_KEYWORDS:
            if k in sql_upper:
                return ValidationResult(is_valid=False, error_message=f"Blocked operation: {k}")

        # 2. Block complex SQL features not supported or inefficient in DynamoDB/PartiQL
        for feature in DynamoDBConstants.UNSUPPORTED_FEATURES:
            if feature in sql_upper:
                return ValidationResult(
                    is_valid=False, 
                    error_message=f"DynamoDB Connector does not support '{feature}'. Use simple SELECT ... WHERE ... syntax."
                )

        return ValidationResult(is_valid=True)
    
    def get_sample_data(self, table: str, limit: int = 5) -> pd.DataFrame:
        # PartiQL syntax: SELECT * FROM "TableName"
        sql = f'SELECT * FROM "{table}"' # Quoting table name is often safer in PartiQL
        # We can also use scan directly but query interface unifies it.
        # But wait, execute_statement doesn't support LIMIT in all contexts easily?
        # Actually PartiQL doesn't strictly support LIMIT in standard way?
        # Docs say: SELECT ... FROM ... [WHERE ...]
        # LIMIT is often client-side or implicit in NextToken.
        # Let's try scan for sample data as it's safer/cheaper.
        try:
             table_res = self.resource.Table(table)
             scan = table_res.scan(Limit=limit)
             return pd.DataFrame(scan.get('Items', []))
        except:
             return pd.DataFrame()
