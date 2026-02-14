import os
import re
import yaml
from typing import Dict, Any, Optional
from loguru import logger

class ConfigLoader:
    """configuration loader with environment variable expansion."""

    @staticmethod
    def load_config(file_path: str = "config/sources.yaml") -> Dict[str, Any]:
        """
        Load YAML configuration file.
        
        Args:
            file_path: Relative path to config file from project root.
            
        Returns:
            Dictionary containing configuration.
        """
        # Resolve absolute path relative to project root (assuming src/utils layout)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        abs_path = os.path.join(project_root, file_path)
        
        if not os.path.exists(abs_path):
            logger.warning(f"Config file not found: {abs_path}")
            return {}
            
        try:
            with open(abs_path, 'r') as f:
                content = f.read()
                
            # Expand environment variables using regex
            # Pattern matches ${VAR_NAME} or $VAR_NAME
            pattern = re.compile(r'\$\{([^}^{]+)\}')
            
            def replace_env(match):
                env_var = match.group(1)
                return os.environ.get(env_var, match.group(0)) # Return original string if env var not found? Or empty?
                # Best practice: Keep literal if not found to avoid silent failures or maybe raise error?
                # Let's keep literal for now to be safe against accidental matches, but log warning?
                # Actually, standard env substitution usually replaces with empty string or default.
                # Let's start with simple replacement.

            expanded_content = pattern.sub(replace_env, content)
            
            return yaml.safe_load(expanded_content) or {}
            
        except Exception as e:
            logger.error(f"Error loading config file {file_path}: {e}")
            return {}

    @staticmethod
    def get_source_config(source_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific data source.
        
        Args:
            source_name: Name of the source in sources.yaml
            
        Returns:
            Configuration dictionary for the source or None if not found.
        """
        config = ConfigLoader.load_config()
        sources = config.get('sources', {})
        
        if source_name not in sources:
            logger.error(f"Source '{source_name}' not found in configuration.")
            return None
            
        return sources[source_name]
