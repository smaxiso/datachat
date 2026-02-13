"""
Gemini LLM provider implementation.

This module provides integration with Google's Gemini models.
"""

from typing import List, Dict, Any, Optional
import google.generativeai as genai
from loguru import logger

from .base import BaseLLMProvider, LLMResponse, LLMConfig, LLMTaskType


class GeminiProvider(BaseLLMProvider):
    """Google Gemini model provider."""
    
    # Prompt templates are inherited from BaseLLMProvider

    def __init__(self, config: LLMConfig):
        """Initialize Gemini provider."""
        super().__init__(config)
        genai.configure(api_key=config.api_key)
        self.model = genai.GenerativeModel(config.model)
        
        # Configure generation config
        self.generation_config = genai.types.GenerationConfig(
            temperature=config.temperature,
            max_output_tokens=config.max_tokens
        )
    
    def _call_gemini(
        self,
        prompt: str,
        task_type: LLMTaskType,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """
        Internal method to call Gemini API.
        
        Args:
            prompt: Prompt to send
            task_type: Type of task
            temperature: Override temperature
            
        Returns:
            LLMResponse
        """
        import time
        max_retries = 3
        base_delay = 10  # Start with 10s delay for 429s

        for attempt in range(max_retries + 1):
            try:
                # Override temperature if needed
                generation_config = self.generation_config
                if temperature is not None:
                    generation_config = genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=self.config.max_tokens
                    )
                
                response = self.model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
                
                content = response.text.strip()
                
                # Gemini usage metadata might not be directly available in simple response
                # We'll try to extract it if available, otherwise it's None
                tokens_used = None
                if hasattr(response, 'usage_metadata'):
                    tokens_used = response.usage_metadata.total_token_count
                
                return LLMResponse(
                    content=content,
                    task_type=task_type,
                    model_used=self.config.model,
                    tokens_used=tokens_used
                )
                
            except Exception as e:
                is_rate_limit = "429" in str(e) or "quota" in str(e).lower()
                
                if is_rate_limit and attempt < max_retries:
                    delay = base_delay * (2 ** attempt)  # 10s, 20s, 40s
                    logger.warning(f"Gemini Rate Limit (429). Retrying in {delay}s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    continue
                
                # If not rate limit or max retries reached
                logger.error(f"Gemini API error: {e}")
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
        
        response = self._call_gemini(
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
        
        response = self._call_gemini(
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
        
        return self._call_gemini(
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
        # Note: Gemini uses a different chat history format, but for simplicity
        # we'll use a clean new chat or try to adapt if needed.
        # For now, we'll treat it as a single turn with history as context if needed.
        
        chat = self.model.start_chat(history=[])
        
        # In a real implementation, we'd map conversation_history to Gemini's format
        # conversation_history is usually [{"role": "user", "content": "..."}, ...]
        
        try:
            response = chat.send_message(message, generation_config=self.generation_config)
            content = response.text.strip()
            
            return LLMResponse(
                content=content,
                task_type=LLMTaskType.CONVERSATION,
                model_used=self.config.model
            )
            
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            return LLMResponse(
                content=f"Error: {str(e)}",
                task_type=LLMTaskType.CONVERSATION,
                model_used=self.config.model,
                metadata={"error": True}
            )
    def classify_intent(self, question: str) -> LLMResponse:
        """Classify user intent."""
        prompt = self.INTENT_CLASSIFICATION_PROMPT.format(question=question)
        
        response = self._call_gemini(
            prompt,
            LLMTaskType.CONVERSATION,
            temperature=0.0
        )
        
        # Clean up response
        content = response.content.strip().upper()
        if "SQL_DATA" in content:
            response.content = "SQL_DATA"
        elif "KNOWLEDGE_BASE" in content:
            response.content = "KNOWLEDGE_BASE"
        else:
            # Default fallback if unclear
            response.content = "SQL_DATA"
            
        return response

    def answer_rag_question(self, question: str, context: str) -> LLMResponse:
        """Answer question using RAG context."""
        prompt = self.RAG_ANSWER_PROMPT.format(
            question=question,
            context=context
        )
        
        return self._call_gemini(
            prompt,
            LLMTaskType.CONVERSATION,
            temperature=0.3
        )
