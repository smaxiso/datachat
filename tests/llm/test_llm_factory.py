import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.llm.factory import LLMFactory
from src.utils.constants import LLMProvider

class TestLLMFactory:
    @patch('src.llm.factory.LLMFactory._load_config_from_env')
    @patch('src.llm.factory.OpenAIProvider')
    def test_create_openai_provider(self, mock_provider, mock_load_config):
        mock_config = MagicMock()
        mock_config.provider = LLMProvider.OPENAI
        mock_load_config.return_value = mock_config
        
        provider = LLMFactory.create_provider()
        assert provider is not None
