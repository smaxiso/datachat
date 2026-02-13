"""
OpenAI LLM provider implementation.

This module provides integration with OpenAI's GPT models.
"""

from typing import List, Dict, Any, Optional
import openai
from loguru import logger

from .base import BaseLLMProvider, LLMResponse, LLMConfig, LLMTaskType


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT model provider."""
    
    # Prompt templates for different tasks
    SQL_GENERATION_PROMPT = """You are a SQL expert. Given a natural language question and database schema, generate a SQL query.

Database Schema:
{schema_context}

{examples_section}

Rules:
- Generate ONLY the SQL query, no explanations
- Use standard SQL syntax
- Include appropriate WHERE, JOIN, GROUP BY, ORDER BY clauses as needed
- For aggregations, include GROUP BY for non-aggregated columns
- Use table aliases for clarity
- Do not include semicolon at the end

Question: {question}

SQL Query:"""

    REFINEMENT_PROMPT = """The following SQL query failed with an error. Fix the query.

Original SQL:
{original_sql}

Error:
{error_message}

Database Schema:
{schema_context}

Generate the corrected SQL query. Return ONLY the SQL, no explanations.

Corrected SQL Query:"""

    INTERPRETATION_PROMPT = """Interpret the following query results and provide business insights.

Original Question: {question}

SQL Query Executed:
{sql}

Results Summary:
{results_summary}

Provide a clear, business-friendly interpretation of these results. Include:
1. Direct answer to the question
2. Key insights or patterns
3. Any notable trends or anomalies
4. Suggested next steps or follow-up questions

Interpretation:"""

    def __init__(self, config: LLMConfig):
        """Initialize OpenAI provider."""
        super().__init__(config)
        openai.api_key = config.api_key
        self.client = openai.OpenAI(api_key=config.api_key)
    
    def _call_openai(
        self,
        prompt: str,
        task_type: LLMTaskType,
        temperature: Optional[float] = None
    ) -> LLMResponse:
        """
        Internal method to call OpenAI API.
        
        Args:
            prompt: Prompt to send
            task_type: Type of task
            temperature: Override temperature
            
        Returns:
            LLMResponse
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a helpful data analysis assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature or self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            content = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if response.usage else None
            
            # Estimate cost (approximate pricing for GPT-4)
            cost = None
            if tokens_used:
                if 'gpt-4' in self.config.model:
                    cost = (tokens_used / 1000) * 0.03  # $0.03 per 1K tokens
                elif 'gpt-3.5' in self.config.model:
                    cost = (tokens_used / 1000) * 0.002  # $0.002 per 1K tokens
            
            return LLMResponse(
                content=content,
                task_type=task_type,
                model_used=self.config.model,
                tokens_used=tokens_used,
                cost=cost
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
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
        
        response = self._call_openai(
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
        
        response = self._call_openai(
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
        
        return self._call_openai(
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
        messages = [
            {"role": "system", "content": "You are a helpful data analysis assistant."}
        ]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            content = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if response.usage else None
            
            return LLMResponse(
                content=content,
                task_type=LLMTaskType.CONVERSATION,
                model_used=self.config.model,
                tokens_used=tokens_used
            )
            
        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            return LLMResponse(
                content=f"Error: {str(e)}",
                task_type=LLMTaskType.CONVERSATION,
                model_used=self.config.model,
                metadata={"error": True}
            )
