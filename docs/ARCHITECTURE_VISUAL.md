# System Architecture Visualization

## Component Interaction Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                           │
│                                                                    │
│  ┌──────────────────────┐         ┌──────────────────────────┐   │
│  │   Streamlit UI       │         │     FastAPI Server       │   │
│  │   (Chat Interface)   │◄───────►│   (REST Endpoints)       │   │
│  │                      │         │                          │   │
│  │  • Chat History      │         │  • POST /api/query       │   │
│  │  • Schema Browser    │         │  • GET  /api/health      │   │
│  │  • Result Display    │         │  • GET  /api/schema      │   │
│  └──────────────────────┘         │  • GET  /api/sources     │   │
│                                   └────────────┬──────────────┘   │
└────────────────────────────────────────────────┼───────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                             │
│                                                                    │
│                    ┌────────────────────────┐                      │
│                    │  Query Orchestrator    │                      │
│                    │  (Main Workflow)       │                      │
│                    └───────────┬────────────┘                      │
│                                │                                   │
│      ┌─────────────────────────┼─────────────────────────┐        │
│      │                         │                         │        │
│      ▼                         ▼                         ▼        │
│  ┌─────────┐            ┌──────────┐            ┌──────────┐     │
│  │ Context │            │   SQL    │            │  Result  │     │
│  │ Builder │            │Generator │            │Interpreter│    │
│  └─────────┘            └──────────┘            └──────────┘     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐      ┌────────────────┐      ┌──────────────────┐
│  LLM ENGINE   │      │ RAG / CONTEXT  │      │  DATA CONNECTOR  │
│               │      │                │      │                  │
│ ┌───────────┐ │      │ ┌────────────┐ │      │ ┌──────────────┐ │
│ │  OpenAI   │ │      │ │ Vector DB  │ │      │ │ PostgreSQL   │ │
│ │ GPT-3.5/4 │ │      │ │  (FAISS)   │ │      │ │  Connector   │ │
│ └───────────┘ │      │ └────────────┘ │      │ └──────────────┘ │
│               │      │                │      │                  │
│ ┌───────────┐ │      │ ┌────────────┐ │      │ ┌──────────────┐ │
│ │Anthropic  │ │      │ │ Embedding  │ │      │ │    MySQL     │ │
│ │  (Future) │ │      │ │  Service   │ │      │ │   (Future)   │ │
│ └───────────┘ │      │ └────────────┘ │      │ └──────────────┘ │
│               │      │                │      │                  │
│ ┌───────────┐ │      │ ┌────────────┐ │      │ ┌──────────────┐ │
│ │  Ollama   │ │      │ │  Metadata  │ │      │ │  BigQuery    │ │
│ │  (Local)  │ │      │ │  Indexer   │ │      │ │   (Future)   │ │
│ └───────────┘ │      │ └────────────┘ │      │ └──────────────┘ │
└───────────────┘      └────────────────┘      └──────────────────┘
```

## Query Processing Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Input                                               │
│    "What are the top 5 customers by revenue?"               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Context Retrieval (RAG)                                  │
│    • Retrieve relevant schema metadata                     │
│    • Get table/column descriptions                         │
│    • Fetch example queries (optional)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. SQL Generation (LLM)                                     │
│    Prompt: Question + Schema Context                       │
│    Output: SELECT c.name, SUM(o.total_amount) as revenue   │
│            FROM customers c JOIN orders o                   │
│            ON c.customer_id = o.customer_id                 │
│            GROUP BY c.name ORDER BY revenue DESC LIMIT 5    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Query Validation                                         │
│    ✓ Check for destructive operations (DROP, DELETE, etc.) │
│    ✓ Verify syntax                                         │
│    ✓ Add LIMIT clause if missing                           │
│    ✓ Check against schema                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
              ┌────────┴────────┐
              │   Valid?        │
              └────┬───────┬────┘
                   │       │
             Yes   │       │   No
                   │       │
                   │       ▼
                   │   ┌──────────────────────┐
                   │   │ 5a. Refine Query     │
                   │   │     (LLM)            │
                   │   └──────────┬───────────┘
                   │              │
                   │              ▼
                   │         (Retry up to 3x)
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Execute Query                                            │
│    • Run against database                                  │
│    • Apply timeout controls                                │
│    • Fetch results                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Interpret Results (LLM)                                  │
│    Input: Original question + SQL + Results                │
│    Output: "Here are your top 5 customers by revenue:      │
│             1. John Doe - $1,329.98                         │
│             2. Frank Wilson - $1,379.98..."                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Return to User                                           │
│    • Natural language interpretation                        │
│    • SQL query (for transparency)                          │
│    • Data table                                            │
│    • Metadata (execution time, row count)                  │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow Example

```
USER QUESTION
    │
    │ "Show me top products by profit margin"
    │
    ▼
ORCHESTRATOR
    │
    ├──► CONTEXT BUILDER ──► Schema: products table
    │                        (name, price, cost, category)
    │
    ├──► LLM (SQL Gen) ──────► Generated SQL:
    │                          SELECT name, category,
    │                          (price - cost) / price * 100
    │                          AS profit_margin
    │                          FROM products
    │                          ORDER BY profit_margin DESC
    │
    ├──► VALIDATOR ──────────► ✓ Safe to execute
    │
    ├──► CONNECTOR ──────────► Execute on PostgreSQL
    │                          Returns: DataFrame with results
    │
    └──► LLM (Interpret) ────► "Your highest margin products are:
                                Wireless Mouse (50.0% margin),
                                Notebook Set (61.5% margin)..."
```

## Security & Safety Flow

```
                    SQL Query
                        │
                        ▼
            ┌───────────────────────┐
            │  Keyword Validation   │
            │  Block: DROP, DELETE, │
            │  UPDATE, TRUNCATE     │
            └───────┬───────────────┘
                    │
                    ▼
            ┌───────────────────────┐
            │  Pattern Detection    │
            │  SQL Injection checks │
            └───────┬───────────────┘
                    │
                    ▼
            ┌───────────────────────┐
            │  Syntax Validation    │
            │  EXPLAIN analysis     │
            └───────┬───────────────┘
                    │
                    ▼
            ┌───────────────────────┐
            │  Automatic Safeguards │
            │  • Add LIMIT clause   │
            │  • Set timeout        │
            │  • Max rows: 10,000   │
            └───────┬───────────────┘
                    │
                    ▼
                  Execute
```

## Technology Stack Map

```
Frontend/UI
    └── Streamlit 1.29.0
        ├── pandas (data display)
        ├── plotly (visualizations)
        └── streamlit-chat

Backend/API
    └── FastAPI 0.104.1
        ├── Pydantic (validation)
        ├── uvicorn (ASGI server)
        └── python-multipart

AI/ML
    ├── LangChain 0.1.0
    │   └── Document processing
    ├── OpenAI 1.6.1
    │   └── GPT-3.5/4 models
    └── sentence-transformers 2.2.2
        └── Embeddings (Stage 2)

Vector Stores (Stage 2)
    ├── FAISS (CPU)
    ├── Chroma (local)
    └── Pinecone (cloud)

Database
    └── SQLAlchemy 2.0.23
        ├── psycopg2-binary (PostgreSQL)
        ├── pymysql (MySQL, future)
        └── pandas (data manipulation)

Dev Tools
    ├── pytest (testing)
    ├── black (formatting)
    ├── mypy (type checking)
    └── loguru (logging)
```
