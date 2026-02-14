import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.llm.openai_provider import OpenAIProvider
from src.llm.base import LLMConfig
from src.utils.constants import LLMProvider, ModelName

class TestOpenAIProvider:
    @pytest.fixture
    def provider(self):
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model=ModelName.GPT_3_5_TURBO,
            api_key='sk-test'
        )
        return OpenAIProvider(config)

    def test_init(self, provider):
        assert provider.client is not None
