# System Architecture - DataChat

## Executive Summary

This document outlines the technical architecture for a composable, RAG-powered GenAI platform that enables natural language querying across multiple data sources. The system is designed with modularity, extensibility, and production-readiness in mind.

---

## Architecture Principles

1. **Modularity**: Each component is independently replaceable
2. **Abstraction**: Standard interfaces for data sources, LLMs, and vector stores
3. **Scalability**: Designed to handle enterprise-scale deployments
4. **Safety**: Query validation and execution controls
5. **Extensibility**: Plugin-based architecture for easy additions

---

## System Layers

### Layer 1: Data Connector Layer

**Purpose**: Provide unified access to heterogeneous data sources

**Components**:
- `BaseConnector` (Abstract Interface)
- `PostgreSQLConnector`
- `MySQLConnector`
- `BigQueryConnector` (Future)
- `SnowflakeConnector` (Future)

**Responsibilities**:
- Schema discovery and metadata extraction
- Query execution with safety controls
- Connection pooling and management
- Data sampling for context

**Interface Contract**:
```python
class BaseConnector:
    def connect() -> Connection
    def get_schema() -> SchemaMetadata
    def execute_query(sql: str) -> QueryResult
    def validate_query(sql: str) -> ValidationResult
    def get_sample_data(table: str, limit: int) -> DataFrame
```

---

### Layer 2: Knowledge & RAG Layer

**Purpose**: Manage metadata, enable semantic search, prevent hallucinations

**Components**:
- `EmbeddingService`: Generate vector embeddings
- `VectorStore`: Store and retrieve embeddings
- `MetadataIndexer`: Index schema and documentation
- `ContextRetriever`: Fetch relevant context for queries

**Data Indexed**:
- Table schemas (columns, types, constraints)
- Table relationships (foreign keys, joins)
- Business glossary and definitions
- Sample queries and use cases
- Column statistics and value distributions

**RAG Pipeline**:
1. User question → Embed query
2. Semantic search in vector store
3. Retrieve top-k relevant metadata chunks
4. Construct enriched context for LLM

**Vector Store Abstraction**:
```python
class BaseVectorStore:
    def add_documents(docs: List[Document])
    def search(query: str, k: int) -> List[Document]
    def delete_collection(name: str)
```

Implementations: FAISS, Chroma, Pinecone, Weaviate

---

### Layer 3: LLM Engine Layer

**Purpose**: Abstract LLM interactions for SQL generation and interpretation

**Components**:
- `BaseLLMProvider` (Abstract Interface)
- `OpenAIProvider`
- `AnthropicProvider`
- `OllamaProvider` (Local)
- `PromptTemplateManager`

**Use Cases**:
1. **SQL Generation**: Convert natural language → SQL
2. **Query Refinement**: Fix syntax errors, optimize queries
3. **Result Interpretation**: Transform raw data → insights
4. **Conversational Memory**: Maintain context across turns

**Provider Interface**:
```python
class BaseLLMProvider:
    def generate_sql(question: str, context: str) -> str
    def interpret_results(query: str, results: DataFrame) -> str
    def refine_query(sql: str, error: str) -> str
```

**Prompt Engineering Strategy**:
- Few-shot examples for SQL generation
- Chain-of-thought reasoning for complex queries
- Schema-aware prompts with relevant metadata
- Error-correction loops with structured feedback

---

### Layer 4: Orchestration & Reasoning Layer

**Purpose**: Core intelligence - coordinate all components to answer questions

**Components**:
- `QueryOrchestrator`: Main workflow controller
- `SQLValidator`: Syntax and safety validation
- `QueryExecutor`: Execute with retries and error handling
- `ContextBuilder`: Assemble RAG context
- `ResponseGenerator`: Format final output

**Query Processing Workflow**:

```
┌─────────────────┐
│  User Question  │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Context Retrieval   │ ◄── RAG Layer
│ (Schema, Examples)  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  SQL Generation     │ ◄── LLM Engine
│  (with context)     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Query Validation   │
│  • Syntax check     │
│  • Safety rules     │
│  • Schema verify    │
└────────┬────────────┘
         │
    ┌────┴────┐
    │  Valid? │
    └────┬────┘
         │ Yes
         ▼
┌─────────────────────┐
│  Query Execution    │ ◄── Data Connector
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ Result Interpret    │ ◄── LLM Engine
│ (Generate insights) │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Response to User   │
└─────────────────────┘
```

**Error Handling**:
- SQL syntax errors → Automatic refinement (max 3 attempts)
- Execution timeouts → Query optimization suggestions
- Empty results → Verification and alternative approaches
- Schema mismatches → Context retrieval improvement

---

### Layer 5: Application Interface Layer

**Purpose**: Expose platform functionality to end users

**Components**:
- `FastAPI Backend`: REST API endpoints
- `Streamlit UI`: Interactive chat interface
- `WebSocket Support`: Real-time streaming
- `Authentication`: JWT-based auth (future)

**API Endpoints**:
```
POST /api/query
    - Body: { "question": str, "data_source": str }
    - Response: { "sql": str, "results": [], "insights": str }

GET /api/sources
    - Response: List of configured data sources

POST /api/index/refresh
    - Refresh RAG metadata index

GET /api/health
    - System health check
```

---

## Data Flow Diagram

```
┌──────────┐
│   User   │
└────┬─────┘
     │ Natural Language Question
     ▼
┌─────────────────┐
│   API Layer     │ (FastAPI)
└────┬────────────┘
     │
     ▼
┌─────────────────────────────────┐
│   Orchestration Layer           │
│  ┌──────────────────────────┐   │
│  │ 1. Retrieve Context (RAG)│   │
│  └───────┬──────────────────┘   │
│          │                      │
│  ┌───────▼──────────────────┐   │
│  │ 2. Generate SQL (LLM)    │   │
│  └───────┬──────────────────┘   │
│          │                      │
│  ┌───────▼──────────────────┐   │
│  │ 3. Validate Query        │   │
│  └───────┬──────────────────┘   │
│          │                      │
│  ┌───────▼──────────────────┐   │
│  │ 4. Execute Query         │   │
│  └───────┬──────────────────┘   │
│          │                      │
│  ┌───────▼──────────────────┐   │
│  │ 5. Interpret Results     │   │
│  └──────────────────────────┘   │
└────┬────────────────────────────┘
     │
     ▼
┌─────────────────┐
│  User Response  │
└─────────────────┘

Supporting Layers:
┌─────────────┐  ┌──────────────┐  ┌─────────────┐
│ Vector DB   │  │  LLM Provider│  │ Data Source │
│  (FAISS)    │  │  (OpenAI)    │  │ (Postgres)  │
└─────────────┘  └──────────────┘  └─────────────┘
```

---

## Technology Stack Details

### Backend Framework
- **FastAPI**: High-performance async API
- **Python 3.10+**: Modern Python features
- **Pydantic**: Data validation and settings

### AI & ML
- **LangChain**: LLM orchestration framework
- **Sentence Transformers**: Embedding generation
- **OpenAI API**: Primary LLM (configurable)
- **tiktoken**: Token counting and management

### Vector Databases
- **FAISS** (Default): CPU-optimized, local deployment
- **Chroma**: Alternative with better persistence
- **Pinecone**: Production-scale cloud option

### Data Access
- **SQLAlchemy**: Database ORM and query builder
- **psycopg2**: PostgreSQL driver
- **pandas**: Data manipulation
- **pyarrow**: Efficient data serialization

### Development Tools
- **pytest**: Testing framework
- **black**: Code formatting
- **mypy**: Type checking
- **pre-commit**: Git hooks

---

## Configuration Management

### Config Structure
```yaml
# config.yaml
llm:
  provider: "openai"  # openai | anthropic | ollama
  model: "gpt-4"
  temperature: 0.1
  max_tokens: 2000

vector_store:
  provider: "faiss"  # faiss | chroma | pinecone
  embedding_model: "all-MiniLM-L6-v2"
  index_path: "./data/vector_index"

data_sources:
  - name: "analytics_db"
    type: "postgresql"
    host: "localhost"
    port: 5432
    database: "analytics"
    schema: "public"

query_execution:
  timeout_seconds: 30
  max_retries: 3
  max_rows: 10000
  allowed_operations: ["SELECT"]
```

---

## Security & Safety

### Query Safety Rules
1. **Read-Only Operations**: Only SELECT queries allowed
2. **No Destructive Commands**: Block DROP, DELETE, UPDATE, TRUNCATE
3. **Timeout Controls**: Configurable query timeouts
4. **Row Limits**: Automatic LIMIT clause injection
5. **SQL Injection Prevention**: Parameterized queries where possible

### Data Access Control
- Database credentials stored in environment variables
- Support for role-based access (future)
- Audit logging of all queries
- PII detection and masking (future)

---

## Scalability Considerations

### Stage 1 (Current)
- Single database connection
- Local vector store (FAISS)
- Synchronous processing
- Single instance deployment

### Future Scalability Path
- **Connection Pooling**: Reuse database connections
- **Async Processing**: Non-blocking I/O for API
- **Distributed Vector Store**: Pinecone, Weaviate
- **Caching Layer**: Redis for frequent queries
- **Load Balancing**: Multiple API instances
- **Queue System**: Celery for long-running queries

---

## Monitoring & Observability

### Metrics to Track
- Query response time (p50, p95, p99)
- SQL generation success rate
- LLM token usage and cost
- Database query execution time
- RAG retrieval relevance scores
- Error rates by type

### Logging Strategy
- Structured JSON logging
- Request/response correlation IDs
- Query execution traces
- LLM prompt/response logging (privacy-aware)

---

## Development Roadmap

### Stage 1: Foundation (Weeks 1-2)
- ✓ Set up project structure
- ✓ Implement PostgreSQL connector
- ✓ Basic LLM integration (OpenAI)
- ✓ Simple SQL generation
- ✓ FastAPI endpoints
- ✓ Streamlit chat UI

### Stage 2: RAG Implementation (Weeks 3-4)
- Schema metadata extraction
- Vector store setup (FAISS)
- Embedding generation pipeline
- Context retrieval integration
- Improved SQL accuracy

### Stage 3: Modularity (Weeks 5-6)
- Abstract LLM provider interface
- Multiple LLM support (OpenAI, Anthropic, Ollama)
- Vector store abstraction
- Configuration-driven provider selection

### Stage 4: Multi-Source (Weeks 7-8)
- Additional data connectors (MySQL, BigQuery)
- Cross-database query support
- Unified metadata schema
- Source selection logic

### Stage 5: Production Features (Weeks 9-10)
- Authentication and authorization
- Advanced error handling
- Query history and analytics
- Performance optimization
- Deployment documentation

---

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock external dependencies
- Edge case coverage

### Integration Tests
- End-to-end query workflows
- Database interaction tests
- LLM provider integration

### Evaluation Metrics
- SQL generation accuracy (compare to ground truth)
- Query execution success rate
- Response relevance (human evaluation)
- Context retrieval precision/recall

---

## Deployment Architecture

### Local Development
```
┌──────────────────────────────────┐
│         Developer Machine        │
│  ┌────────────┐  ┌─────────────┐ │
│  │  FastAPI   │  │  Streamlit  │ │
│  └─────┬──────┘  └──────┬──────┘ │
│        │                │        │
│  ┌─────▼────────────────▼──────┐ │
│  │   Local PostgreSQL DB       │ │
│  └─────────────────────────────┘ │
│  ┌─────────────────────────────┐ │
│  │   FAISS Vector Store        │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘
```

### Production (Future)
```
┌─────────────────────────────────────┐
│           Cloud Platform            │
│  ┌──────────────┐  ┌──────────────┐ │
│  │ Load Balancer│  │  API Gateway │ │
│  └──────┬───────┘  └──────┬───────┘ │
│         │                 │         │
│  ┌──────▼─────────────────▼──────┐  │
│  │   FastAPI (Multiple Instances)│  │
│  └──────┬────────────────────────┘  │
│         │                           │
│  ┌──────▼─────────┐  ┌────────────┐ │
│  │  Vector DB     │  │  Cache     │ │
│  │  (Pinecone)    │  │  (Redis)   │ │
│  └────────────────┘  └────────────┘ │
│  ┌─────────────────────────────────┐│
│  │   Data Sources (Cloud DBs)      ││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
```

---

## Cost Optimization

### LLM Costs
- Use smaller models for simple queries (GPT-3.5 vs GPT-4)
- Cache frequent query patterns
- Implement prompt compression
- Consider local models (Ollama) for dev/test

### Infrastructure Costs
- Start with local vector store (FAISS)
- Use managed databases where cost-effective
- Implement query result caching
- Monitor token usage per request

---

## Risk Mitigation

### Technical Risks
1. **LLM Hallucinations**: Mitigated by RAG, validation
2. **Query Performance**: Timeout controls, optimization
3. **Schema Changes**: Automated re-indexing
4. **Cost Overruns**: Token limits, caching, monitoring

### Security Risks
1. **SQL Injection**: Parameterized queries, validation
2. **Data Leakage**: Access controls, query auditing
3. **API Abuse**: Rate limiting, authentication

---

## Success Metrics

### Technical Metrics
- SQL accuracy: >85% on benchmark queries
- Query success rate: >95%
- Average response time: <5 seconds
- RAG context relevance: >80%

### Business Metrics
- Time saved per query vs manual SQL
- User adoption rate
- Query complexity handled
- Cost per query

---

## Conclusion

This architecture provides a solid foundation for building a production-ready GenAI data intelligence platform. The modular design ensures easy extensibility while maintaining safety and performance.

Key strengths:
- Composable, plugin-based architecture
- Production-ready safety controls
- Clear path to scalability
- Multiple deployment options
- Cost-conscious design

Next steps: Begin Stage 1 implementation with PostgreSQL connector and basic SQL generation.
