"""
PostgreSQL data source connector implementation.

This module provides a concrete implementation of the BaseConnector for PostgreSQL databases.
"""

import re
import time
from typing import List, Dict, Any, Optional
import pandas as pd
from sqlalchemy import create_engine, text, inspect, MetaData
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


class PostgreSQLConnector(BaseConnector):
    """PostgreSQL database connector."""
    
    # SQL keywords that are not allowed for safety
    BLOCKED_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
        'INSERT', 'UPDATE', 'GRANT', 'REVOKE'
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PostgreSQL connector.
        
        Args:
            config: Configuration dictionary with keys:
                - host: Database host
                - port: Database port
                - database: Database name
                - username: Database username
                - password: Database password
                - schema: Schema name (default: 'public')
        """
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5432)
        self.database = config['database']
        self.username = config['username']
        self.password = config['password']
        self.schema = config.get('schema', 'public')
        self.engine = None
        
    def connect(self) -> bool:
        """Establish connection to PostgreSQL database."""
        try:
            connection_string = (
                f"postgresql://{self.username}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=5,
                max_overflow=10
            )
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to PostgreSQL: {self.database}")
            return True
            
        except SQLAlchemyError as e:
            self._status = ConnectionStatus.ERROR
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Close the database connection."""
        try:
            if self.engine:
                self.engine.dispose()
                self._status = ConnectionStatus.DISCONNECTED
                logger.info(f"Disconnected from PostgreSQL: {self.database}")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False
    
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
        inspector = inspect(self.engine)
        tables = []
        
        for table_name in inspector.get_table_names(schema=self.schema):
            columns = []
            
            # Get column information
            for col in inspector.get_columns(table_name, schema=self.schema):
                column_meta = ColumnMetadata(
                    name=col['name'],
                    data_type=str(col['type']),
                    nullable=col['nullable'],
                    primary_key=False  # Will be updated below
                )
                columns.append(column_meta)
            
            # Mark primary keys
            pk_constraint = inspector.get_pk_constraint(table_name, schema=self.schema)
            if pk_constraint:
                pk_columns = pk_constraint.get('constrained_columns', [])
                for col in columns:
                    if col.name in pk_columns:
                        col.primary_key = True
            
            # Get foreign keys
            fks = inspector.get_foreign_keys(table_name, schema=self.schema)
            for fk in fks:
                for col_name in fk['constrained_columns']:
                    for col in columns:
                        if col.name == col_name:
                            ref_table = fk['referred_table']
                            ref_col = fk['referred_columns'][0]
                            col.foreign_key = f"{ref_table}.{ref_col}"
            
            # Get row count
            row_count = self._get_table_row_count(table_name)
            
            table_meta = TableMetadata(
                name=table_name,
                schema=self.schema,
                columns=columns,
                row_count=row_count
            )
            tables.append(table_meta)
        
        # Get relationships
        relationships = self._extract_relationships(inspector)
        
        return SchemaMetadata(
            source_name=self.database,
            source_type="postgresql",
            tables=tables,
            relationships=relationships
        )
    
    def _get_table_row_count(self, table_name: str) -> int:
        """Get approximate row count for a table."""
        try:
            query = text(f"""
                SELECT reltuples::bigint AS estimate
                FROM pg_class
                WHERE relname = :table_name
            """)
            with self.engine.connect() as conn:
                result = conn.execute(query, {"table_name": table_name})
                count = result.scalar()
                return int(count) if count else 0
        except Exception:
            return 0
    
    def _extract_relationships(self, inspector) -> List[Dict[str, Any]]:
        """Extract foreign key relationships."""
        relationships = []
        
        for table_name in inspector.get_table_names(schema=self.schema):
            fks = inspector.get_foreign_keys(table_name, schema=self.schema)
            for fk in fks:
                relationships.append({
                    'from_table': table_name,
                    'from_column': fk['constrained_columns'][0],
                    'to_table': fk['referred_table'],
                    'to_column': fk['referred_columns'][0]
                })
        
        return relationships
    
    def validate_query(self, sql: str) -> ValidationResult:
        """Validate SQL query for safety and syntax."""
        sql_upper = sql.upper()
        warnings = []
        
        # Check for blocked keywords
        for keyword in self.BLOCKED_KEYWORDS:
            if re.search(rf'\b{keyword}\b', sql_upper):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Query contains blocked keyword: {keyword}",
                    warnings=warnings
                )
        
        # Ensure it's a SELECT query
        if not sql_upper.strip().startswith('SELECT'):
            return ValidationResult(
                is_valid=False,
                error_message="Only SELECT queries are allowed",
                warnings=warnings
            )
        
        # Check for potential SQL injection patterns
        suspicious_patterns = [
            r";\s*DROP",
            r";\s*DELETE",
            r"--\s*",
            r"\/\*.*\*\/",
            r"UNION\s+SELECT",
            r"EXEC\s*\(",
            r"EXECUTE\s*\("
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, sql_upper):
                warnings.append(f"Suspicious pattern detected: {pattern}")
        
        # Try to validate syntax by using EXPLAIN
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"EXPLAIN {sql}"))
        except SQLAlchemyError as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Syntax error: {str(e)}",
                warnings=warnings
            )
        
        return ValidationResult(
            is_valid=True,
            warnings=warnings
        )
    
    def execute_query(
        self,
        sql: str,
        params: Optional[Dict] = None,
        timeout: int = 30
    ) -> QueryResult:
        """Execute SQL query with safety controls."""
        start_time = time.time()
        
        # Validate query first
        validation = self.validate_query(sql)
        if not validation.is_valid:
            return QueryResult(
                success=False,
                error_message=validation.error_message,
                sql_executed=sql
            )
        
        try:
            # Add LIMIT if not present to prevent huge result sets
            if 'LIMIT' not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT 10000"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(sql), params or {})
                
                # Fetch results
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                execution_time = time.time() - start_time
                
                return QueryResult(
                    success=True,
                    data=df,
                    row_count=len(df),
                    execution_time=execution_time,
                    sql_executed=sql
                )
                
        except SQLAlchemyError as e:
            execution_time = time.time() - start_time
            return QueryResult(
                success=False,
                error_message=str(e),
                execution_time=execution_time,
                sql_executed=sql
            )
    
    def get_sample_data(self, table: str, limit: int = 5) -> pd.DataFrame:
        """Retrieve sample data from a table."""
        sql = f"SELECT * FROM {self.schema}.{table} LIMIT {limit}"
        result = self.execute_query(sql)
        
        if result.success:
            return result.data
        else:
            logger.error(f"Failed to get sample data: {result.error_message}")
            return pd.DataFrame()
