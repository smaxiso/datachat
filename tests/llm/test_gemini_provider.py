import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.llm.gemini_provider import GeminiProvider
from src.llm.base import LLMConfig
from src.utils.constants import LLMProvider, ModelName

class TestGeminiProvider:
    @pytest.fixture
    def provider(self):
        config = LLMConfig(
            provider=LLMProvider.GEMINI,
            model=ModelName.GEMINI_PRO,
            api_key='fake-key'
        )
        return GeminiProvider(config)

    def test_init(self, provider):
        assert provider.model.model_name == f'models/{ModelName.GEMINI_PRO.value}'
