"""
BigQuery data source connector implementation.

This module provides a concrete implementation of the BaseConnector for Google BigQuery.
"""

import os
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

try:
    from google.oauth2 import service_account
except ImportError:
    service_account = None

from src.connectors.base import (
    BaseConnector,
    SchemaMetadata,
    TableMetadata,
    ColumnMetadata,
    QueryResult,
    ValidationResult,
    ConnectionStatus
)
from src.utils.constants import BigQueryConstants


class BigQueryConnector(BaseConnector):
    """Google BigQuery connector."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize BigQuery connector.
        
        Args:
            config: Configuration dictionary with keys:
                - connection_string: SQLAlchemy connection string (bigquery://project/dataset)
                - credentials_path: Path to service account JSON key (optional)
        """
        super().__init__(config)
        self.connection_string = config.get('connection_string', '')
        self.credentials_path = config.get('credentials_path')
        self.engine = None
        
        # Parse project_id and dataset_id from bigquery://project/dataset
        self.project_id = None
        self.dataset_id = None
        if self.connection_string.startswith('bigquery://'):
            parts = self.connection_string.replace('bigquery://', '').split('/')
            if len(parts) >= 1:
                self.project_id = parts[0]
            if len(parts) >= 2:
                self.dataset_id = parts[1]
        
    def connect(self) -> bool:
        """Establish connection to BigQuery."""
        try:
            connect_args = {}
            if self.credentials_path:
                if not os.path.exists(self.credentials_path):
                    logger.error(f"Credentials file not found: {self.credentials_path}")
                    return False
                # We don't strictly need to pass credentials object if env var is set,
                # but explicit path support is good.
                # SQLAlchemy-BigQuery handles this via credentials_path if we were using the older style
                # or we can rely on GOOGLE_APPLICATION_CREDENTIALS env var if set.
                # However, sqlalchemy-bigquery often prefers credentials_path in create_engine if provided.
                # Let's trust standard auth flow if path not provided.
                
                # Actually, sqlalchemy-bigquery supports 'credentials_path' in connect_args?
                # Or we can just set the env var for this process if provided.
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.credentials_path

            self.engine = create_engine(
                self.connection_string,
                credentials_path=self.credentials_path
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to BigQuery: {self.connection_string}")
            return True
            
        except SQLAlchemyError as e:
            self._status = ConnectionStatus.ERROR
            logger.error(f"Failed to connect to BigQuery: {e}")
            return False
        except ImportError:
            logger.error("sqlalchemy-bigquery or google-cloud-bigquery not installed.")
            return False
    
    def disconnect(self) -> bool:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            self._status = ConnectionStatus.DISCONNECTED
        return True
    
    def test_connection(self) -> bool:
        """Test if connection is alive."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    
    def get_schema(self) -> SchemaMetadata:
        """Retrieve complete schema metadata."""
        if not self.engine:
             raise RuntimeError("Database not connected")

        inspector = inspect(self.engine)
        tables = []
        
        for table_name in inspector.get_tables_names(): # Note: some dialects differ in method name? typical is get_table_names
             # sqlalchemy-bigquery uses get_table_names
             pass
        
        # In BigQuery, schema usually refers to 'dataset'.
        for table_name in inspector.get_table_names():
            columns = []
            
            for col in inspector.get_columns(table_name):
                column_meta = ColumnMetadata(
                    name=col['name'],
                    data_type=str(col['type']),
                    nullable=col['nullable'],
                    primary_key=False, # BQ doesn't strictly enforce PKs like RDBMS
                    description=col.get('comment')
                )
                columns.append(column_meta)
            
            # BigQuery doesn't support enforcing Foreign Keys in traditional sense usually provided by inspector
            # So we skip FK extraction for now or rely on manual metadata if needed.
            
            row_count = self._get_table_row_count(table_name)
            
            table_meta = TableMetadata(
                name=table_name,
                schema='default', # dataset is in connection string
                columns=columns,
                row_count=row_count
            )
            tables.append(table_meta)
        
        return SchemaMetadata(
            source_name="BigQuery",
            source_type="bigquery",
            tables=tables,
            relationships=[] # No FKs extracted automatically
        )
    
    def _get_table_row_count(self, table_name: str) -> int:
        """Get row count (approximation for BQ seems hard check metadata?)."""
        # COUNT(*) in BQ is cheap/free if from metadata, but 'SELECT COUNT(*)' scans nothing?
        # Actually in BQ SELECT COUNT(*) is optimized.
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return int(result.scalar())
        except Exception:
            return 0

    def execute_query(
        self,
        sql: str,
        params: Optional[Dict] = None,
        timeout: int = 30
    ) -> QueryResult:
        # Re-use similar logic to MySQL/Postgres but strictly read-only check
        validation = self.validate_query(sql)
        if not validation.is_valid:
            return QueryResult(success=False, error_message=validation.error_message)

        try:
            if 'LIMIT' not in sql.upper():
                 sql += " LIMIT 1000" # Stronger default limit for BQ costs
            
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                
                return QueryResult(
                    success=True,
                    data=df,
                    row_count=len(df),
                    sql_executed=sql
                )
        except Exception as e:
            return QueryResult(success=False, error_message=str(e), sql_executed=sql)

    def validate_query(self, sql: str) -> ValidationResult:
        sql_upper = sql.upper()
        for keyword in BigQueryConstants.BLOCKED_KEYWORDS:
             if keyword in sql_upper: # Simple check
                 return ValidationResult(is_valid=False, error_message=f"Blocked: {keyword}")
        return ValidationResult(is_valid=True)

    def get_sample_data(self, table: str, limit: int = 5) -> pd.DataFrame:
        return self.execute_query(f"SELECT * FROM {table} LIMIT {limit}").data

