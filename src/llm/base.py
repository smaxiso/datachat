"""
Base LLM provider interface.

This module defines the abstract interface for all LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class LLMTaskType(Enum):
    """Types of tasks that LLMs can perform."""
    SQL_GENERATION = "sql_generation"
    QUERY_REFINEMENT = "query_refinement"
    RESULT_INTERPRETATION = "result_interpretation"
    CONVERSATION = "conversation"


@dataclass
class LLMResponse:
    """Response from an LLM."""
    content: str
    task_type: LLMTaskType
    model_used: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""
    provider: str
    model: str
    temperature: float = 0.1
    max_tokens: int = 2000
    api_key: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    Supports multiple LLM backends (OpenAI, Anthropic, Ollama, etc.)
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize LLM provider.
        
        Args:
            config: LLM configuration
        """
        self.config = config
    
    @abstractmethod
    def generate_sql(
        self,
        question: str,
        schema_context: str,
        examples: Optional[List[str]] = None
    ) -> LLMResponse:
        """
        Generate SQL query from natural language question.
        
        Args:
            question: Natural language question
            schema_context: Relevant schema and metadata
            examples: Optional few-shot examples
            
        Returns:
            LLMResponse containing generated SQL
        """
        pass
    
    @abstractmethod
    def refine_query(
        self,
        original_sql: str,
        error_message: str,
        schema_context: str
    ) -> LLMResponse:
        """
        Refine a SQL query that failed execution.
        
        Args:
            original_sql: The SQL that failed
            error_message: Error message from execution
            schema_context: Relevant schema information
            
        Returns:
            LLMResponse containing refined SQL
        """
        pass
    
    @abstractmethod
    def interpret_results(
        self,
        question: str,
        sql: str,
        results_summary: str
    ) -> LLMResponse:
        """
        Interpret query results into business insights.
        
        Args:
            question: Original user question
            sql: SQL query that was executed
            results_summary: Summary of query results
            
        Returns:
            LLMResponse containing interpretation
        """
        pass
    
    @abstractmethod
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> LLMResponse:
        """
        Handle conversational interactions.
        
        Args:
            message: User message
            conversation_history: Previous conversation context
            
        Returns:
            LLMResponse containing chat response
        """
        pass
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'provider': self.config.provider,
            'model': self.config.model,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens
        }
