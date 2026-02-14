"""
Query orchestrator - Core intelligence layer.

This module coordinates all components to answer natural language questions.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import pandas as pd
import hashlib
import time
from loguru import logger
from src.utils.cache import cache_response

from src.connectors.base import BaseConnector, QueryResult
from src.llm.base import BaseLLMProvider
from src.orchestration.metrics import QueryMetrics
from src.utils.constants import OrchestrationConstants
try:
    from src.rag.embeddings import EmbeddingService
    from src.rag.vector_store import VectorStore
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("RAG dependencies not available")


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = {
            "success": self.success,
            "question": self.question,
            "sql_generated": self.sql_generated,
            "interpretation": self.interpretation,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "data": None
        }
        if self.data is not None and not self.data.empty:
            d["data"] = self.data.to_dict(orient='records')
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'QueryResponse':
        """Create from dictionary."""
        data = None
        if d.get("data"):
            data = pd.DataFrame(d["data"])
        
        return cls(
            success=d["success"],
            question=d["question"],
            sql_generated=d.get("sql_generated"),
            data=data,
            interpretation=d.get("interpretation"),
            error_message=d.get("error_message"),
            metadata=d.get("metadata")
        )


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
        max_retries: Optional[int] = None
    ):
        """
        Initialize orchestrator.
        
        Args:
            connector: Data source connector
            llm_provider: LLM provider for SQL generation
            max_retries: Maximum number of query refinement attempts (defaults to LLM config)
        """
        self.connector = connector
        self.llm = llm_provider
        self.max_retries = max_retries if max_retries is not None else llm_provider.config.max_retries
        
        # Initialize RAG components if available
        self.embeddings = None
        self.vector_store = None
        if RAG_AVAILABLE:
            try:
                self.embeddings = EmbeddingService()
                self.vector_store = VectorStore()
                logger.info("RAG components initialized in Orchestrator")
            except Exception as e:
                logger.error(f"Failed to initialize RAG: {e}")
        
        # Initialize Cache
        self._schema_cache = None
        self._schema_cache_time = None
        self._query_cache = {}  # MD5 hash -> QueryResponse
        self.metrics = QueryMetrics()
    
    @cache_response(ttl=300, prefix="query", deserializer=QueryResponse.from_dict)
    def process_question(self, question: str) -> QueryResponse:
        """
        Process a natural language question end-to-end.
        
        Args:
            question: Natural language question
            
        Returns:
            QueryResponse with results and interpretation
        """
        logger.info(f"Processing question: {question}")
        start_time = time.time()
        
        # Check cache
        question_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()
        if question_hash in self._query_cache:
            logger.info("Returning cached response")
            # For cached queries, we don't record them in metrics again to avoid double counting,
            # or we could record them as lightning fast queries. Let's skip for now as per plan.
            return self._query_cache[question_hash]
        
        try:
            # Step 1: Classify Intent (if RAG is active)
            intent = "SQL_DATA"
            if self.vector_store and self.vector_store.count() > 0:
                intent_response = self.llm.classify_intent(question)
                intent = intent_response.content
                logger.info(f"Classified Intent: {intent}")
            
            if intent == "KNOWLEDGE_BASE":
                response = self._handle_rag_query(question)
                return response
                
            # Step 2: SQL Flow (Default)
            # Get schema context
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
                response = QueryResponse(
                    success=False,
                    question=question,
                    sql_generated=sql,
                    error_message=query_result.error_message
                )
                return response
            
            # Step 4: Interpret results
            interpretation = self._interpret_results(
                question, query_result.sql_executed, query_result.data
            )
            
            # Step 5: Build response
            response = QueryResponse(
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
            
            # Cache successful results
            if response.success:
                self._query_cache[question_hash] = response
                
            return response
            
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return QueryResponse(
                success=False,
                question=question,
                error_message=f"Unexpected error: {str(e)}"
            )
        finally:
            if 'response' in locals() and response:
                execution_time = time.time() - start_time
                self.metrics.record_query(
                    success=response.success,
                    tokens=response.metadata.get('tokens_used') if response.metadata else None,
                    cost=response.metadata.get('cost') if response.metadata else None,
                    time_seconds=execution_time
                )
    
    def _build_schema_context(self) -> str:
        """
        Build schema context for LLM.
        
        In Stage 1, this simply retrieves all schema information.
        In Stage 2+, this will use RAG to retrieve only relevant context.
        
        Returns:
            Formatted schema context string
        """
        now = time.time()
        if self._schema_cache and self._schema_cache_time and (now - self._schema_cache_time < OrchestrationConstants.SCHEMA_CACHE_TTL):
            return self._schema_cache
            
        schema = self.connector.get_schema()
        
        context_parts = [
            f"Database: {schema.source_name}",
            f"Type: {schema.source_type}",
            "\nTables:\n"
        ]
        
        # Build enhanced schema context with categorical values
        for table in schema.tables:
            context_parts.append(f"\nTable: {table.name}")
            if table.row_count:
                context_parts.append(f"  Rows: ~{table.row_count}")
            
            context_parts.append("  Columns:")
            for col in table.columns:
                pk_marker = " [PK]" if col.primary_key else ""
                fk_marker = f" [FK -> {col.foreign_key}]" if col.foreign_key else ""
                nullable = "NULL" if col.nullable else "NOT NULL"
                
                col_desc = (
                    f"    - {col.name}: {col.data_type} {nullable}{pk_marker}{fk_marker}"
                )
                
                # Heuristic for categorical columns: string types, not PK/FK
                # In a real app, strict cardinality checks would be better
                is_categorical = (
                    "CHAR" in col.data_type.upper() or 
                    "TEXT" in col.data_type.upper() or 
                    "STRING" in col.data_type.upper()
                ) and not col.primary_key and not col.foreign_key
                
                if is_categorical:
                    try:
                        # Fetch distinct values (limit to n to avoid bloating context)
                        values = self.connector.get_unique_values(table.name, col.name, limit=OrchestrationConstants.CAT_VALUES_LIMIT)
                        if values and len(values) > 0:
                            # Only show if not too many distinct values (pseudo-cardinality check)
                            # In production, we'd check count distinct first
                             col_desc += f" [Values: {', '.join(map(str, values))}]"
                    except Exception as e:
                        # Fail gracefully if fetching values fails
                        logger.warning(f"Could not fetch unique values for {table.name}.{col.name}: {e}")
                        
                context_parts.append(col_desc)
                
        # Add relationships
        if schema.relationships:
            context_parts.append("\nRelationships:")
            for rel in schema.relationships:
                context_parts.append(
                    f"  - {rel['from_table']}.{rel['from_column']} -> "
                    f"{rel['to_table']}.{rel['to_column']}"
                )
        
        context = "\n".join(context_parts)
        self._schema_cache = context
        self._schema_cache_time = now
        return context
    
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
                f"\n\nFirst few rows:\n{data.head(OrchestrationConstants.RESULT_SUMMARY_ROWS).to_string()}"
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
    
    @cache_response(ttl=3600, prefix="schema")
    def get_schema_summary(self) -> str:
        """
        Get a human-readable summary of the database schema.
        
        Returns:
            Schema summary
        """
        return self._build_schema_context()

    def _handle_rag_query(self, question: str) -> QueryResponse:
        """
        Handle a RAG (Knowledge Base) query.
        
        Args:
            question: User question
            
        Returns:
            QueryResponse
        """
        logger.info("Handling RAG query...")
        
        try:
            # 1. Generate embedding
            query_embedding = self.embeddings.generate_embedding(question)
            if not query_embedding:
                return QueryResponse(success=False, question=question, error_message="Failed to generate embedding")
                
            # 2. Retrieve documents
            results = self.vector_store.query_similar(query_embedding, n_results=3)
            documents = results.get('documents', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            
            if not documents:
                return QueryResponse(
                    success=True,
                    question=question,
                    interpretation="I looked through the knowledge base but couldn't find any relevant documents."
                )
                
            # Format context
            context_parts = []
            for i, doc in enumerate(documents):
                source = metadatas[i].get('filename', 'Unknown')
                context_parts.append(f"Source: {source}\nContent:\n{doc}\n")
                
            context = "\n---\n".join(context_parts)
            
            # 3. Generate Answer
            answer_response = self.llm.answer_rag_question(question, context)
            
            return QueryResponse(
                success=True,
                question=question,
                interpretation=answer_response.content,
                metadata={
                    "source_docs": metadatas,
                    "rag_mode": True
                }
            )
            
        except Exception as e:
            logger.error(f"RAG Error: {e}")
            return QueryResponse(success=False, question=question, error_message=str(e))
