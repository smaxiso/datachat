"""
SQLite data source connector implementation.

This module provides a concrete implementation of the BaseConnector for SQLite databases.
"""

import os
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


class SQLiteConnector(BaseConnector):
    """SQLite database connector."""
    
    # SQL keywords that are not allowed for safety
    BLOCKED_KEYWORDS = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
        'INSERT', 'UPDATE', 'GRANT', 'REVOKE', 'ATTACH', 'DETACH'
    ]
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize SQLite connector.
        
        Args:
            config: Configuration dictionary with keys:
                - database: Path to SQLite database file
        """
        super().__init__(config)
        self.database_path = config['database']
        self.engine = None
        
    def connect(self) -> bool:
        """Establish connection to SQLite database."""
        try:
            # Ensure directory exists if path contains directory
            db_dir = os.path.dirname(self.database_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                
            connection_string = f"sqlite:///{self.database_path}"
            
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self._status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to SQLite: {self.database_path}")
            return True
            
        except SQLAlchemyError as e:
            self._status = ConnectionStatus.ERROR
            logger.error(f"Failed to connect to SQLite: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Close the database connection."""
        try:
            if self.engine:
                self.engine.dispose()
                self._status = ConnectionStatus.DISCONNECTED
                logger.info(f"Disconnected from SQLite: {self.database_path}")
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
        relationships = []
        
        for table_name in inspector.get_table_names():
            # Get columns
            columns = []
            for col in inspector.get_columns(table_name):
                columns.append(ColumnMetadata(
                    name=col['name'],
                    data_type=str(col['type']),
                    nullable=col['nullable'],
                    primary_key=col.get('primary_key', False),
                    foreign_key=None,  # We'll update this later
                    description=col.get('comment')
                ))
            
            # Get foreign keys to build relationships
            fks = inspector.get_foreign_keys(table_name)
            for fk in fks:
                # Add to relationships list
                relationships.append({
                    'from_table': table_name,
                    'from_column': fk['constrained_columns'][0],
                    'to_table': fk['referred_table'],
                    'to_column': fk['referred_columns'][0]
                })
                
                # Update column metadata
                for col in columns:
                    if col.name == fk['constrained_columns'][0]:
                        col.foreign_key = f"{fk['referred_table']}.{fk['referred_columns'][0]}"
            
            # Get row count (careful with large tables)
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = result.scalar()
            except Exception:
                row_count = None
            
            tables.append(TableMetadata(
                name=table_name,
                schema='main',  # SQLite default schema is 'main'
                columns=columns,
                row_count=row_count
            ))
            
        return SchemaMetadata(
            source_name=os.path.basename(self.database_path),
            source_type="sqlite",
            tables=tables,
            relationships=relationships
        )
    
    def execute_query(self, sql: str, params: Optional[Dict] = None) -> QueryResult:
        """Execute a SQL query."""
        if not self.engine:
            return QueryResult(success=False, error_message="Database not connected")
            
        start_time = time.time()
        
        try:
            # Simple safety check first
            validation = self.validate_query(sql)
            if not validation.is_valid:
                return QueryResult(
                    success=False,
                    error_message=f"Query validation failed: {validation.error_message}",
                    sql_executed=sql
                )
            
            with self.engine.connect() as conn:
                # Execute query
                result = conn.execute(text(sql), params or {})
                
                # For SELECT queries, return dataframe
                if result.returns_rows:
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    row_count = len(df)
                    execution_time = time.time() - start_time
                    
                    return QueryResult(
                        success=True,
                        data=df,
                        row_count=row_count,
                        execution_time=execution_time,
                        sql_executed=sql
                    )
                else:
                    # For non-SELECT queries (though we block most)
                    execution_time = time.time() - start_time
                    return QueryResult(
                        success=True,
                        row_count=result.rowcount,
                        execution_time=execution_time,
                        sql_executed=sql
                    )
                    
        except SQLAlchemyError as e:
            return QueryResult(
                success=False,
                error_message=str(e),
                sql_executed=sql,
                execution_time=time.time() - start_time
            )
    
    def validate_query(self, sql: str) -> ValidationResult:
        """Validate a SQL query."""
        sql_upper = sql.upper()
        warnings = []
        
        # Check for blocked keywords
        for keyword in self.BLOCKED_KEYWORDS:
            # Use regex to match whole words only
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
        
        # Try to validate syntax by using EXPLAIN QUERY PLAN (SQLite equivalent of EXPLAIN)
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"EXPLAIN QUERY PLAN {sql}"))
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
    
    def get_sample_data(self, table: str, limit: int = 5) -> pd.DataFrame:
        """Retrieve sample data from a table."""
        try:
            with self.engine.connect() as conn:
                query = text(f"SELECT * FROM {table} LIMIT :limit")
                result = conn.execute(query, {"limit": limit})
                return pd.DataFrame(result.fetchall(), columns=result.keys())
        except Exception as e:
            logger.error(f"Error fetching sample data: {e}")
            return pd.DataFrame()

    def get_unique_values(self, table: str, column: str, limit: int = 50) -> List[Any]:
        """Get unique values for a column (SQLite implementation)."""
        try:
            # Simple distinct query for SQLite
            sql = f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL LIMIT {limit}"
            result = self.execute_query(sql)
            
            if result.success and result.data is not None and not result.data.empty:
                return result.data.iloc[:, 0].tolist()
            return []
        except Exception as e:
            logger.warning(f"Failed to get unique values for {table}.{column}: {e}")
            return []
