"""
Data Connector Factory.

This module provides a factory for creating data source connectors.
"""

from typing import Optional, Dict, Any
import os
from loguru import logger

from .base import BaseConnector
from .postgresql import PostgreSQLConnector
from .sqlite import SQLiteConnector


class ConnectorFactory:
    """Factory for creating data connectors."""
    
    @staticmethod
    def create_connector() -> BaseConnector:
        """
        Create a data connector instance based on environment configuration.
        
        Returns:
            BaseConnector instance
        """
        db_type = os.getenv('DB_TYPE', 'postgres').lower()
        
        logger.info(f"Initializing database connector: {db_type}")
        
        if db_type == 'postgres':
            config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 5432)),
                'database': os.getenv('DB_NAME', 'analytics'),
                'username': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'postgres'),
                'schema': os.getenv('DB_SCHEMA', 'public')
            }
            return PostgreSQLConnector(config)
            
        elif db_type == 'sqlite':
            db_name = os.getenv('DB_NAME', 'data/analytics.db')
            
            # If path is relative, resolve it relative to project root
            if not os.path.isabs(db_name):
                 # Get project root (assuming src/connectors/factory.py layout)
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                db_name = os.path.join(project_root, db_name)
                
            config = {
                'database': db_name
            }
            return SQLiteConnector(config)
            
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
