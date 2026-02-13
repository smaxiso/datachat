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

    # Enhanced Prompt Templates
    SQL_GENERATION_PROMPT = """You are an expert SQL Data Analyst. Your goal is to generate a precise, syntactically correct SQL query to answer the user's question based on the provided schema.

Database Schema:
{schema_context}

{examples_section}

Critical Constraints & Rules:
1. **SQL Only**: Generate ONLY the SQL query. Do not provide explanations, markdown formatting (no ```sql), or comments.
2. **Syntax**: Use standard SQL. Ensure all tables and columns exist in the schema.
3. **Joins**: 
   - Use explicit `JOIN` clauses (e.g., `JOIN table ON table.id = other.id`).
   - Never use comma-separated tables in `FROM` unless absolutely necessary.
   - checking for foreign keys in the schema description to determine join conditions.
4. **Aggregations**: 
   - When using `COUNT`, `SUM`, `AVG`, `MAX`, `MIN`, you MUST include a `GROUP BY` clause for all non-aggregated columns.
5. **Filtering**:
   - Use `WHERE` clauses to filter data.
   - For strings, handle case-sensitivity if necessary (e.g., `LOWER(col) = 'value'`).
   - For dates, ensure you compare compatible formats.
6. **Formatting**:
   - Use table aliases (e.g., `t1`, `t2` or meaningful abbreviations) for clarity.
   - Do not include a trailing semicolon `;`.

User Question: {question}

SQL Query:"""

    REFINEMENT_PROMPT = """The following SQL query failed to execute. Your task is to fix the query based on the error message.

Original SQL:
{original_sql}

Error Message:
{error_message}

Database Schema:
{schema_context}

Instructions:
1. Analyze the error message to identify the issue (e.g., missing column, syntax error, wrong group by).
2. Refer to the schema to verify table/column names.
3. Generate the CORRECTED SQL query.
4. Output ONLY the SQL, no explanations or markdown.

Corrected SQL Query:"""

    INTERPRETATION_PROMPT = """You are a Senior Data Analyst. Interpret the results of the following SQL query to provide actionable business insights.

Original Question: {question}

SQL Query Executed:
{sql}

Query Results:
{results_summary}

Instructions:
1. **Direct Answer**: Start with a direct, concise answer to the question.
2. **Analysis**: Explain *why* this result matters or what patterns you see.
3. **Context**: Mention any limitations or assumptions based on the data provided.
4. **Tone**: Professional, business-focused, and helpful.

Interpretation:"""

    RAG_ANSWER_PROMPT = """You are a knowledgeable assistant. Answer the user's question based strictly on the provided context.

Context:
{context}

Question:
{question}

Instructions:
1. Use ONLY the information in the context.
2. If the context doesn't contain the answer, say "I cannot answer this based on the available information."
3. Be concise and professional.

Answer:"""

    INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier. Determine if the user's question requires querying a structured Database (SQL) or a Knowledge Base (Text/Policies).

User Question: {question}

Instructions:
1. Output `SQL_DATA` if the question is about numbers, statistics, table records, or aggregations (e.g., "how many orders", "total revenue", "list customers").
2. Output `KNOWLEDGE_BASE` if the question is about policies, procedures, shipping, refunds, or general information (e.g., "what is the refund policy", "how to return").
3. Output ONLY the classification label.

Classification:"""
    
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
    
    @abstractmethod
    def classify_intent(self, question: str) -> LLMResponse:
        """
        Classify the user intent (SQL vs RAG).
        
        Args:
            question: User question
            
        Returns:
            LLMResponse containing classification
        """
        pass
        
    @abstractmethod
    def answer_rag_question(self, question: str, context: str) -> LLMResponse:
        """
        Answer a question using retrieved context.
        
        Args:
            question: User question
            context: Retrieved context documents
            
        Returns:
            LLMResponse containing answer
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
