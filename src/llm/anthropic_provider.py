"""
Anthropic LLM provider implementation.

This module provides integration with Anthropic's Claude models.
"""

from typing import List, Dict, Any, Optional
import anthropic
from loguru import logger

from .base import BaseLLMProvider, LLMResponse, LLMConfig, LLMTaskType


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude model provider."""
    
    # Prompt templates are inherited from BaseLLMProvider

    def __init__(self, config: LLMConfig):
        """Initialize Anthropic provider."""
        super().__init__(config)
        self.client = anthropic.Anthropic(api_key=config.api_key)
    
    def _call_anthropic(
        self,
        prompt: str,
        task_type: LLMTaskType,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """
        Internal method to call Anthropic API.
        
        Args:
            prompt: Prompt to send
            task_type: Type of task
            temperature: Override temperature
            
        Returns:
            LLMResponse
        """
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=temperature or self.config.temperature,
                system="You are a helpful data analysis assistant.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text.strip()
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            return LLMResponse(
                content=content,
                task_type=task_type,
                model_used=self.config.model,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return LLMResponse(
                content=f"Error: {str(e)}",
                task_type=task_type,
                model_used=self.config.model,
                metadata={"error": True}
            )
    
    def generate_sql(
        self,
        question: str,
        schema_context: str,
        examples: Optional[List[str]] = None
    ) -> LLMResponse:
        """Generate SQL from natural language."""
        # Format examples section
        examples_section = ""
        if examples:
            examples_section = "Example Queries:\n" + "\n".join(
                f"- {ex}" for ex in examples
            )
        
        prompt = self.SQL_GENERATION_PROMPT.format(
            question=question,
            schema_context=schema_context,
            examples_section=examples_section
        )
        
        response = self._call_anthropic(
            prompt,
            LLMTaskType.SQL_GENERATION,
            temperature=0.0  # Use zero temperature for SQL generation
        )
        
        # Clean up the SQL (remove markdown code blocks if present)
        sql = response.content
        if sql.startswith('```sql'):
            sql = sql[6:]
        if sql.startswith('```'):
            sql = sql[3:]
        if sql.endswith('```'):
            sql = sql[:-3]
        sql = sql.strip()
        
        response.content = sql
        return response
    
    def refine_query(
        self,
        original_sql: str,
        error_message: str,
        schema_context: str
    ) -> LLMResponse:
        """Refine a failed SQL query."""
        prompt = self.REFINEMENT_PROMPT.format(
            original_sql=original_sql,
            error_message=error_message,
            schema_context=schema_context
        )
        
        response = self._call_anthropic(
            prompt,
            LLMTaskType.QUERY_REFINEMENT,
            temperature=0.0
        )
        
        # Clean up the SQL
        sql = response.content
        if sql.startswith('```sql'):
            sql = sql[6:]
        if sql.startswith('```'):
            sql = sql[3:]
        if sql.endswith('```'):
            sql = sql[:-3]
        sql = sql.strip()
        
        response.content = sql
        return response
    
    def interpret_results(
        self,
        question: str,
        sql: str,
        results_summary: str
    ) -> LLMResponse:
        """Interpret query results."""
        prompt = self.INTERPRETATION_PROMPT.format(
            question=question,
            sql=sql,
            results_summary=results_summary
        )
        
        return self._call_anthropic(
            prompt,
            LLMTaskType.RESULT_INTERPRETATION,
            temperature=0.3  # Slightly higher temperature for interpretation
        )
    
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> LLMResponse:
        """Handle conversational interactions."""
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system="You are a helpful data analysis assistant.",
                messages=messages
            )
            
            content = response.content[0].text.strip()
            tokens_used = response.usage.input_tokens + response.usage.output_tokens
            
            return LLMResponse(
                content=content,
                task_type=LLMTaskType.CONVERSATION,
                model_used=self.config.model,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"Anthropic chat error: {e}")
            return LLMResponse(
                content=f"Error: {str(e)}",
                task_type=LLMTaskType.CONVERSATION,
                model_used=self.config.model,
                metadata={"error": True}
            )
