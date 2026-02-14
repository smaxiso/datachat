import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import os
import pytest
from unittest.mock import patch
from src.utils.config_loader import ConfigLoader


class TestConfigLoader:
    def test_load_config_with_env_vars(self):
        with patch.dict(os.environ, {'TEST_VAR': 'value'}):
            loader = ConfigLoader()
            # testing expansion logic
            result = loader._expand_env_vars("${TEST_VAR}")
            assert result == "value"
