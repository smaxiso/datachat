import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.llm.anthropic_provider import AnthropicProvider
from src.llm.base import LLMConfig
from src.utils.constants import LLMProvider, ModelName

class TestAnthropicProvider:
    @pytest.fixture
    def provider(self):
        config = LLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model=ModelName.CLAUDE_3_SONNET,
            api_key='sk-ant-test'
        )
        return AnthropicProvider(config)

    def test_init(self, provider):
        assert provider.client is not None
