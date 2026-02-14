"""
LLM Provider Factory.

This module provides a factory for creating LLM providers.
"""

from typing import Optional, Dict, Any
import os
from loguru import logger

from .base import BaseLLMProvider, LLMConfig
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .anthropic_provider import AnthropicProvider
from src.utils.constants import LLMProvider, ModelName


class LLMFactory:
    """Factory for creating LLM providers."""
    
    @staticmethod
    def create_provider(config: Optional[LLMConfig] = None) -> BaseLLMProvider:
        """
        Create an LLM provider instance.
        
        Args:
            config: LLM configuration. If None, loads from environment.
            
        Returns:
            BaseLLMProvider instance
        """
        if config is None:
            config = LLMFactory._load_config_from_env()
            
        logger.info(f"Initializing LLM provider: {config.provider} (model: {config.model})")
        
        if config.provider.lower() == LLMProvider.OPENAI:
            return OpenAIProvider(config)
        elif config.provider.lower() == LLMProvider.GEMINI:
            return GeminiProvider(config)
        elif config.provider.lower() == LLMProvider.ANTHROPIC:
            return AnthropicProvider(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")
    
    @staticmethod
    def _load_config_from_env() -> LLMConfig:
        """Load configuration from environment variables."""
        provider = os.getenv('LLM_PROVIDER', LLMProvider.OPENAI).lower()
        
        # Default models per provider
        default_models = {
            LLMProvider.OPENAI: ModelName.GPT_3_5_TURBO,
            LLMProvider.GEMINI: ModelName.GEMINI_PRO,
            LLMProvider.ANTHROPIC: ModelName.CLAUDE_3_SONNET
        }
        
        # Default API keys
        api_keys = {
            LLMProvider.OPENAI: os.getenv('OPENAI_API_KEY'),
            LLMProvider.GEMINI: os.getenv('GOOGLE_API_KEY'),
            LLMProvider.ANTHROPIC: os.getenv('ANTHROPIC_API_KEY')
        }
        
        model = os.getenv('LLM_MODEL', default_models.get(provider, ''))
        api_key = api_keys.get(provider)
        
        if not api_key:
            logger.warning(f"API key for {provider} not found in environment variables.")
            
        return LLMConfig(
            provider=provider,
            model=model,
            temperature=float(os.getenv('LLM_TEMPERATURE', 0.1)),
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', 2000)),
            api_key=api_key
        )
