from enum import Enum

class DBType(str, Enum):
    """Supported database types."""
    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    BIGQUERY = "bigquery"
    REDSHIFT = "redshift"
    DYNAMODB = "dynamodb"

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    MOCK = "mock"

class LLMTaskType(str, Enum):
    """Types of LLM tasks."""
    SQL_GENERATION = "sql_generation"
    CONVERSATION = "conversation"
    CORRECTION = "correction"
    INTENT_CLASSIFICATION = "intent_classification"
    RAG_ANSWER = "rag_answer"

class ModelName(str, Enum):
    """Common LLM model names."""
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    GEMINI_PRO = "gemini-pro"


class ValidationPatterns:
    """Common patterns for query validation."""
    # Basic DML/DDL that modifies data
    DESTRUCTIVE_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER",
        "TRUNCATE", "GRANT", "REVOKE"
    ]

class RedshiftConstants:
    """Redshift-specific constants and limits."""
    # Extends destructive keywords with Redshift-specific heavy operations
    BLOCKED_KEYWORDS = ValidationPatterns.DESTRUCTIVE_KEYWORDS + [
        "VACUUM", "ANALYZE", "COPY", "UNLOAD"
    ]


class DynamoDBConstants:
    """DynamoDB-specific constants."""
    # PartiQL supports DML, but we block it for analytics safety
    BLOCKED_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT", "CREATE", "ALTER"
    ]

    # SQL features not efficiently supported by PartiQL
    UNSUPPORTED_FEATURES = [
        "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN",
        "GROUP BY", "HAVING", "UNION", "INTERSECT", "EXCEPT"
    ]


class SQLiteConstants:
    """SQLite-specific constants."""
    BLOCKED_KEYWORDS = ValidationPatterns.DESTRUCTIVE_KEYWORDS + [
        "ATTACH", "DETACH"
    ]


class PostgresConstants:
    """PostgreSQL-specific constants."""
    BLOCKED_KEYWORDS = ValidationPatterns.DESTRUCTIVE_KEYWORDS


class MySQLConstants:
    """MySQL-specific constants."""
    BLOCKED_KEYWORDS = ValidationPatterns.DESTRUCTIVE_KEYWORDS


class BigQueryConstants:
    """BigQuery-specific constants."""
    BLOCKED_KEYWORDS = ValidationPatterns.DESTRUCTIVE_KEYWORDS


class OrchestrationConstants:
    """Constants for Query Orchestrator."""
    SCHEMA_CACHE_TTL = 300  # 5 minutes
    DEFAULT_SQL_LIMIT = 5000
    CAT_VALUES_LIMIT = 10
    RESULT_SUMMARY_ROWS = 10


class RAGConstants:
    """Constants for RAG components."""
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200
    VECTOR_DB_DIR = "data/chroma"
    COLLECTION_NAME = "datachat_docs"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    CONTEXT_DOCS_COUNT = 3


class LLMDefaults:
    """Default values for LLM configurations."""
    TEMPERATURE = 0.1
    MAX_TOKENS = 2000
    MAX_RETRIES = 3
    RETRY_DELAY = 10


class AppMetadata:
    """Branding and Metadata for the application."""
    TITLE = "GenAI Data Intelligence"
    ICON = "🤖"
    FOOTER = "DataChat v1.2 | Powered by LLMs and RAG"
    API_TIMEOUT = 5
    QUERY_TIMEOUT = 60
