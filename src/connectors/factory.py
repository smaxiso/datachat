"""
Data Connector Factory.

This module provides a factory for creating data source connectors.
"""

from typing import Optional, Dict, Any
from loguru import logger
import os
from src.utils.config_loader import ConfigLoader

from .base import BaseConnector
from .postgresql import PostgreSQLConnector
from .sqlite import SQLiteConnector
from .mysql import MySQLConnector
from .bigquery import BigQueryConnector
from .redshift import RedshiftConnector
from .dynamodb import DynamoDBConnector
from src.utils.constants import DBType


class ConnectorFactory:
    """Factory for creating data connectors."""
    
    @staticmethod
    def create_connector() -> BaseConnector:
        """
        Create a data connector instance based on configuration.
        
        Uses ACTIVE_SOURCE environment variable to select source from config/sources.yaml.
        Defaults to 'local_sqlite' if not set.
        
        Returns:
            BaseConnector instance
        """
        active_source = os.getenv('ACTIVE_SOURCE', 'local_sqlite')
        logger.info(f"Initializing connector for source: {active_source}")
        
        # Load configuration
        config_loader = ConfigLoader()
        source_config = config_loader.get_source_config(active_source)
        
        if not source_config:
            legacy_db_type = os.getenv('DB_TYPE')
            if legacy_db_type:
                logger.warning(f"Source '{active_source}' not found in config. Falling back to DB_TYPE='{legacy_db_type}'")
                return ConnectorFactory._create_legacy_connector(legacy_db_type)
            
            error_msg = f"Source '{active_source}' not found in configuration and DB_TYPE not set."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        db_type = source_config.get('type')
        config = source_config.get('config', {})
        
        if db_type == DBType.POSTGRES:
            return PostgreSQLConnector(config)
        elif db_type == DBType.MYSQL:
            return MySQLConnector(config)
        elif db_type == DBType.BIGQUERY:
            return BigQueryConnector(config)
        elif db_type == DBType.REDSHIFT:
            return RedshiftConnector(config)
        elif db_type == DBType.DYNAMODB:
            return DynamoDBConnector(config)
        elif db_type == DBType.SQLITE:
            # Handle relative path resolution here or in loader?
            # Loader does env expansion, but relative path logic for SQLite specific?
            # Let's keep the logic here for now or update config to absolute path.
            # config/sources.yaml usually has "data/analytics.db" relative to project root.
            # But SQLiteConnector expects absolute path or CWD relative.
            # Let's resolve if it looks relative.
            db_name = config.get('database')
            if db_name and db_name != ':memory:' and not os.path.isabs(db_name):
                 # Get project root
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                config['database'] = os.path.join(project_root, db_name)
            return SQLiteConnector(config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    @staticmethod
    def _create_legacy_connector(db_type: str) -> BaseConnector:
        """Fallback method for legacy environment variables."""
        db_type = db_type.lower()
        if db_type == DBType.POSTGRES:
            config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 5432)),
                'database': os.getenv('DB_NAME', 'analytics'),
                'username': os.getenv('DB_USER', 'postgres'),
                'password': os.getenv('DB_PASSWORD', 'postgres'),
                'schema': os.getenv('DB_SCHEMA', 'public')
            }
            return PostgreSQLConnector(config)
            
        elif db_type == DBType.MYSQL:
            config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', 3306)),
                'database': os.getenv('DB_NAME', 'analytics'),
                'username': os.getenv('DB_USER', 'root'),
                'password': os.getenv('DB_PASSWORD', ''),
            }
            return MySQLConnector(config)

        elif db_type == DBType.BIGQUERY:
            config = {
                'connection_string': f"bigquery://{os.getenv('DB_PROJECT_ID')}/{os.getenv('DB_DATASET')}",
                'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            }
            return BigQueryConnector(config)
            
        elif db_type == DBType.SQLITE:
            db_name = os.getenv('DB_NAME', 'data/analytics.db')
            if db_name != ':memory:' and not os.path.isabs(db_name):
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                db_name = os.path.join(project_root, db_name)
            config = {'database': db_name}
            return SQLiteConnector(config)
            
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
