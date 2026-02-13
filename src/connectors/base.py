"""
Base connector interface for data sources.

This module defines the abstract interface that all data connectors must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import pandas as pd


class ConnectionStatus(Enum):
    """Connection status enumeration."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ColumnMetadata:
    """Metadata for a single column."""
    name: str
    data_type: str
    nullable: bool
    primary_key: bool
    foreign_key: Optional[str] = None
    description: Optional[str] = None


@dataclass
class TableMetadata:
    """Metadata for a database table."""
    name: str
    schema: str
    columns: List[ColumnMetadata]
    row_count: Optional[int] = None
    description: Optional[str] = None


@dataclass
class SchemaMetadata:
    """Complete schema metadata for a data source."""
    source_name: str
    source_type: str
    tables: List[TableMetadata]
    relationships: List[Dict[str, Any]]


@dataclass
class QueryResult:
    """Result of a query execution."""
    success: bool
    data: Optional[pd.DataFrame] = None
    row_count: int = 0
    execution_time: float = 0.0
    error_message: Optional[str] = None
    sql_executed: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of query validation."""
    is_valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors.
    
    All connectors must implement these methods to provide a unified interface
    for interacting with different data sources.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the connector with configuration.
        
        Args:
            config: Configuration dictionary containing connection parameters
        """
        self.config = config
        self.connection = None
        self._status = ConnectionStatus.DISCONNECTED
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data source.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close the connection to the data source.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if the connection is alive and healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> SchemaMetadata:
        """
        Retrieve complete schema metadata from the data source.
        
        Returns:
            SchemaMetadata: Complete schema information including tables and columns
        """
        pass
    
    @abstractmethod
    def execute_query(self, sql: str, params: Optional[Dict] = None) -> QueryResult:
        """
        Execute a SQL query on the data source.
        
        Args:
            sql: SQL query string
            params: Optional parameters for parameterized queries
            
        Returns:
            QueryResult: Query execution result with data and metadata
        """
        pass
    
    @abstractmethod
    def validate_query(self, sql: str) -> ValidationResult:
        """
        Validate a SQL query without executing it.
        
        Checks for:
        - Syntax errors
        - Security issues (SQL injection, destructive operations)
        - Schema compatibility
        
        Args:
            sql: SQL query string to validate
            
        Returns:
            ValidationResult: Validation result with any errors or warnings
        """
        pass
    
    @abstractmethod
    def get_sample_data(self, table: str, limit: int = 5) -> pd.DataFrame:
        """
        Retrieve sample data from a table.
        
        Args:
            table: Table name
            limit: Number of rows to retrieve (default: 5)
            
        Returns:
            DataFrame: Sample data from the table
        """
        pass
    
    def get_unique_values(self, table: str, column: str, limit: int = 50) -> List[Any]:
        """
        Get unique values for a column.
        
        Args:
            table: Table name
            column: Column name
            limit: Maximum number of values to return
            
        Returns:
            List of unique values
        """
        # Simple SQL generation - connectors can override if needed
        sql = f"SELECT DISTINCT {column} FROM {table} LIMIT {limit}"
        # Some DBs might need quoting, but we'll assume standard SQL for now
        # or rely on the fact that existing code doesn't quote strictly yet
        
        result = self.execute_query(sql)
        
        if result.success and result.data is not None and not result.data.empty:
            # Drop metadata/None values
            values = result.data.iloc[:, 0].dropna().tolist()
            return values
        return []

    def get_table_names(self) -> List[str]:
        """
        Get list of all table names in the data source.
        
        Returns:
            List of table names
        """
        schema = self.get_schema()
        return [table.name for table in schema.tables]
    
    def get_status(self) -> ConnectionStatus:
        """
        Get current connection status.
        
        Returns:
            ConnectionStatus: Current status of the connection
        """
        return self._status
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
