"""
Query orchestrator - Core intelligence layer.

This module coordinates all components to answer natural language questions.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import pandas as pd
from loguru import logger

from src.connectors.base import BaseConnector, QueryResult
from src.llm.base import BaseLLMProvider


@dataclass
class QueryResponse:
    """Complete response to a user question."""
    success: bool
    question: str
    sql_generated: Optional[str] = None
    data: Optional[pd.DataFrame] = None
    interpretation: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class QueryOrchestrator:
    """
    Main orchestrator that coordinates all components.
    
    Workflow:
    1. Receive natural language question
    2. Retrieve relevant schema context (future: from RAG)
    3. Generate SQL using LLM
    4. Validate and execute query
    5. Interpret results
    6. Return formatted response
    """
    
    def __init__(
        self,
        connector: BaseConnector,
        llm_provider: BaseLLMProvider,
        max_retries: int = 3
    ):
        """
        Initialize orchestrator.
        
        Args:
            connector: Data source connector
            llm_provider: LLM provider for SQL generation
            max_retries: Maximum number of query refinement attempts
        """
        self.connector = connector
        self.llm = llm_provider
        self.max_retries = max_retries
    
    def process_question(self, question: str) -> QueryResponse:
        """
        Process a natural language question end-to-end.
        
        Args:
            question: Natural language question
            
        Returns:
            QueryResponse with results and interpretation
        """
        logger.info(f"Processing question: {question}")
        
        try:
            # Step 1: Get schema context
            schema_context = self._build_schema_context()
            
            # Step 2: Generate SQL
            sql_response = self.llm.generate_sql(
                question=question,
                schema_context=schema_context
            )
            sql = sql_response.content
            logger.info(f"Generated SQL: {sql}")
            
            # Step 3: Execute with retry logic
            query_result = self._execute_with_retry(sql, schema_context)
            
            if not query_result.success:
                return QueryResponse(
                    success=False,
                    question=question,
                    sql_generated=sql,
                    error_message=query_result.error_message
                )
            
            # Step 4: Interpret results
            interpretation = self._interpret_results(
                question, query_result.sql_executed, query_result.data
            )
            
            # Step 5: Build response
            return QueryResponse(
                success=True,
                question=question,
                sql_generated=query_result.sql_executed,
                data=query_result.data,
                interpretation=interpretation,
                metadata={
                    'row_count': query_result.row_count,
                    'execution_time': query_result.execution_time,
                    'tokens_used': sql_response.tokens_used,
                    'cost': sql_response.cost
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return QueryResponse(
                success=False,
                question=question,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _build_schema_context(self) -> str:
        """
        Build schema context for LLM.
        
        In Stage 1, this simply retrieves all schema information.
        In Stage 2+, this will use RAG to retrieve only relevant context.
        
        Returns:
            Formatted schema context string
        """
        schema = self.connector.get_schema()
        
        context_parts = [
            f"Database: {schema.source_name}",
            f"Type: {schema.source_type}",
            "\nTables:\n"
        ]
        
        for table in schema.tables:
            context_parts.append(f"\nTable: {table.name}")
            if table.row_count:
                context_parts.append(f"  Rows: ~{table.row_count}")
            
            context_parts.append("  Columns:")
            for col in table.columns:
                pk_marker = " [PK]" if col.primary_key else ""
                fk_marker = f" [FK -> {col.foreign_key}]" if col.foreign_key else ""
                nullable = "NULL" if col.nullable else "NOT NULL"
                context_parts.append(
                    f"    - {col.name}: {col.data_type} {nullable}{pk_marker}{fk_marker}"
                )
        
        # Add relationships
        if schema.relationships:
            context_parts.append("\nRelationships:")
            for rel in schema.relationships:
                context_parts.append(
                    f"  - {rel['from_table']}.{rel['from_column']} -> "
                    f"{rel['to_table']}.{rel['to_column']}"
                )
        
        return "\n".join(context_parts)
    
    def _execute_with_retry(
        self,
        sql: str,
        schema_context: str,
        attempt: int = 1
    ) -> QueryResult:
        """
        Execute query with automatic retry and refinement on errors.
        
        Args:
            sql: SQL query to execute
            schema_context: Schema context for refinement
            attempt: Current attempt number
            
        Returns:
            QueryResult
        """
        # Validate query
        validation = self.connector.validate_query(sql)
        if not validation.is_valid:
            if attempt >= self.max_retries:
                return QueryResult(
                    success=False,
                    error_message=f"Validation failed: {validation.error_message}",
                    sql_executed=sql
                )
            
            # Try to refine
            logger.warning(f"Query validation failed, attempting refinement (attempt {attempt})")
            refined = self.llm.refine_query(
                original_sql=sql,
                error_message=validation.error_message,
                schema_context=schema_context
            )
            return self._execute_with_retry(refined.content, schema_context, attempt + 1)
        
        # Execute query
        result = self.connector.execute_query(sql)
        
        if not result.success:
            if attempt >= self.max_retries:
                return result
            
            # Try to refine
            logger.warning(f"Query execution failed, attempting refinement (attempt {attempt})")
            refined = self.llm.refine_query(
                original_sql=sql,
                error_message=result.error_message,
                schema_context=schema_context
            )
            return self._execute_with_retry(refined.content, schema_context, attempt + 1)
        
        return result
    
    def _interpret_results(
        self,
        question: str,
        sql: str,
        data: pd.DataFrame
    ) -> str:
        """
        Interpret query results into business insights.
        
        Args:
            question: Original question
            sql: SQL that was executed
            data: Query results
            
        Returns:
            Human-readable interpretation
        """
        # Build results summary
        if data.empty:
            results_summary = "No results found."
        else:
            # Create a concise summary
            summary_parts = [
                f"Returned {len(data)} rows",
                f"\nColumns: {', '.join(data.columns)}",
                f"\n\nFirst few rows:\n{data.head(10).to_string()}"
            ]
            
            # Add basic statistics for numeric columns
            numeric_cols = data.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                summary_parts.append("\n\nNumeric column statistics:")
                for col in numeric_cols:
                    summary_parts.append(
                        f"  {col}: min={data[col].min()}, "
                        f"max={data[col].max()}, "
                        f"avg={data[col].mean():.2f}"
                    )
            
            results_summary = "".join(summary_parts)
        
        # Get interpretation from LLM
        interpretation_response = self.llm.interpret_results(
            question=question,
            sql=sql,
            results_summary=results_summary
        )
        
        return interpretation_response.content
    
    def get_schema_summary(self) -> str:
        """
        Get a human-readable summary of the database schema.
        
        Returns:
            Schema summary
        """
        return self._build_schema_context()
