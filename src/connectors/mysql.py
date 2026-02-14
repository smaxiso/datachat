"""
MySQL data source connector implementation.

This module provides a concrete implementation of the BaseConnector for MySQL databases.
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
from src.utils.constants import MySQLConstants


class MySQLConnector(BaseConnector):
    """MySQL database connector."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize MySQL connector.
        
        Args:
            config: Configuration dictionary with keys:
                - host: Database host
                - port: Database port
                - database: Database name
                - username: Database username
                - password: Database password
        """
        super().__init__(config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 3306)
        self.database = config['database']
        self.username = config['username']
        self.password = config['password']
        self.engine = None
        
    def connect(self) -> bool:
        """Establish connection to MySQL database."""
        try:
            # MySQL connection string using pymysql
            connection_string = (
                f"mysql+pymysql://{self.username}:{self.password}"
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
            logger.info(f"Connected to MySQL: {self.database}")
            return True
            
        except SQLAlchemyError as e:
            self._status = ConnectionStatus.ERROR
            logger.error(f"Failed to connect to MySQL: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Close the database connection."""
        try:
            if self.engine:
                self.engine.dispose()
                self._status = ConnectionStatus.DISCONNECTED
                logger.info(f"Disconnected from MySQL: {self.database}")
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
        if not self.engine:
             raise RuntimeError("Database not connected")

        inspector = inspect(self.engine)
        tables = []
        
        # In MySQL, schema is essentially the database name
        for table_name in inspector.get_table_names():
            columns = []
            
            # Get column information
            for col in inspector.get_columns(table_name):
                column_meta = ColumnMetadata(
                    name=col['name'],
                    data_type=str(col['type']),
                    nullable=col['nullable'],
                    primary_key=False  # Will be updated below
                )
                columns.append(column_meta)
            
            # Mark primary keys
            pk_constraint = inspector.get_pk_constraint(table_name)
            if pk_constraint:
                pk_columns = pk_constraint.get('constrained_columns', [])
                for col in columns:
                    if col.name in pk_columns:
                        col.primary_key = True
            
            # Get foreign keys
            fks = inspector.get_foreign_keys(table_name)
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
                schema=self.database,
                columns=columns,
                row_count=row_count
            )
            tables.append(table_meta)
        
        # Get relationships
        relationships = self._extract_relationships(inspector)
        
        return SchemaMetadata(
            source_name=self.database,
            source_type="mysql",
            tables=tables,
            relationships=relationships
        )
    
    def _get_table_row_count(self, table_name: str) -> int:
        """Get approximate row count for a table."""
        try:
            # Use information_schema for MySQL estimate
            query = text(f"""
                SELECT table_rows
                FROM information_schema.tables
                WHERE table_schema = :database
                  AND table_name = :table_name
            """)
            with self.engine.connect() as conn:
                result = conn.execute(query, {
                    "database": self.database,
                    "table_name": table_name
                })
                count = result.scalar()
                return int(count) if count is not None else 0
        except Exception:
            # Fallback to COUNT(*) if estimate fails (slower but reliable)
             try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    return int(result.scalar())
             except Exception:
                return 0
    
    def _extract_relationships(self, inspector) -> List[Dict[str, Any]]:
        """Extract foreign key relationships."""
        relationships = []
        
        for table_name in inspector.get_table_names():
            fks = inspector.get_foreign_keys(table_name)
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
        for keyword in MySQLConstants.BLOCKED_KEYWORDS:
            if re.search(rf'\b{keyword}\b', sql_upper):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Query contains blocked keyword: {keyword}",
                    warnings=warnings
                )
        
        # Ensure it's a SELECT query
        if not sql_upper.strip().startswith('SELECT') and not sql_upper.strip().startswith('WITH'):
             return ValidationResult(
                is_valid=False,
                error_message="Only SELECT queries are allowed",
                warnings=warnings
            )
        
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
            # MySQL LIMIT syntax is just "LIMIT N" at the end
            if 'LIMIT' not in sql.upper():
                sql = f"{sql.strip().rstrip(';')} LIMIT 10000"
            
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
        sql = f"SELECT * FROM {table} LIMIT {limit}"
        result = self.execute_query(sql)
        
        if result.success:
            return result.data
        else:
            logger.error(f"Failed to get sample data: {result.error_message}")
            return pd.DataFrame()

    def get_unique_values(self, table: str, column: str, limit: int = 50) -> List[Any]:
        """Get unique values for a column (MySQL implementation)."""
        try:
            sql = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL LIMIT {limit}"
            result = self.execute_query(sql)
            
            if result.success and result.data is not None and not result.data.empty:
                return result.data.iloc[:, 0].tolist()
            return []
        except Exception as e:
            logger.warning(f"Failed to get unique values for {table}.{column}: {e}")
            return []
