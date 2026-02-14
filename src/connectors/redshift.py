"""
Redshift data source connector implementation.

This module provides a concrete implementation of the BaseConnector for AWS Redshift.
"""

import re
import time
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from src.connectors.base import (
    BaseConnector,
    SchemaMetadata,
    TableMetadata,
    ColumnMetadata,
    QueryResult,
    ValidationResult,
    ConnectionStatus
)
from src.utils.constants import RedshiftConstants


class RedshiftConnector(BaseConnector):
    """AWS Redshift connector."""
    
    """AWS Redshift connector."""
    
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Redshift connector.
        
        Args:
            config: Configuration dictionary with keys:
                - host: Database host
                - port: Database port (default 5439)
                - database: Database name
                - username: Database username
                - password: Database password
                - schema: Schema name (default: 'public')
        """
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5439)
        self.database = config['database']
        self.username = config['username']
        self.password = config['password']
        self.schema = config.get('schema', 'public')
        self.engine = None
        
    def connect(self) -> bool:
        """Establish connection to Redshift."""
        try:
            # utilizing sqlalchemy-redshift dialect
            connection_string = (
                f"redshift+psycopg2://{self.username}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                connect_args={'sslmode': 'prefer'} # AWS often requires SSL
            )
            
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to Redshift: {self.database}")
            return True
            
        except SQLAlchemyError as e:
            self._status = ConnectionStatus.ERROR
            logger.error(f"Failed to connect to Redshift: {e}")
            return False
            
    def disconnect(self) -> bool:
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            self._status = ConnectionStatus.DISCONNECTED
        return True
    
    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_schema(self) -> SchemaMetadata:
        """Retrieve schema metadata."""
        if not self.engine:
             raise RuntimeError("Database not connected")
             
        inspector = inspect(self.engine)
        tables = []
        
        for table_name in inspector.get_table_names(schema=self.schema):
            columns = []
            for col in inspector.get_columns(table_name, schema=self.schema):
                column_meta = ColumnMetadata(
                    name=col['name'],
                    data_type=str(col['type']),
                    nullable=col['nullable'],
                    primary_key=False # Logic to extract PK if needed
                )
                columns.append(column_meta)
                
            # Redshift supports PKs but they are informational only.
            # We can still extract them using get_pk_constraint if strictly needed.
            
            row_count = self._get_table_row_count(table_name)
            
            tables.append(TableMetadata(
                name=table_name,
                schema=self.schema,
                columns=columns,
                row_count=row_count
            ))
            
        return SchemaMetadata(
            source_name=self.database,
            source_type="redshift",
            tables=tables,
            relationships=[] # Can implement FK extraction similar to Postgres
        )

    def _get_table_row_count(self, table_name: str) -> int:
        """Get approximate row count from SVV_TABLE_INFO."""
        try:
            sql = f"""
                SELECT "table", "rows"
                FROM svv_table_info
                WHERE "schema" = '{self.schema}' AND "table" = '{table_name}'
            """
            with self.engine.connect() as conn:
                 result = conn.execute(text(sql)).fetchone()
                 if result:
                     return int(result[1])
                 else:
                     # Fallback to COUNT(*)
                     return super()._get_table_row_count(table_name) # Assuming base has it or implement direct
        except Exception:
             return 0

    def execute_query(self, sql: str, params: Optional[Dict] = None, timeout: int = 30) -> QueryResult:
        # Similar safety checks as Postgres
        validation = self.validate_query(sql)
        if not validation.is_valid:
            return QueryResult(success=False, error_message=validation.error_message)

        try:
            start_time = time.time()
            if 'LIMIT' not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT 5000" # Lower default limit for Redshift
            
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
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
        sql_upper = sql.upper()
        for keyword in RedshiftConstants.BLOCKED_KEYWORDS:
             if re.search(rf'\b{keyword}\b', sql_upper):
                 return ValidationResult(is_valid=False, error_message=f"Blocked: {keyword}")
        
        return ValidationResult(is_valid=True)
    
    def get_sample_data(self, table: str, limit: int = 5) -> pd.DataFrame:
        sql = f"SELECT * FROM {self.schema}.{table} LIMIT {limit}"
        return self.execute_query(sql).data
