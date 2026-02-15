# DataChat

A modular, RAG-powered GenAI platform that enables natural language querying across multiple data sources.

## 🎯 Overview

This platform acts as an intelligent interface layer between users and data infrastructure, converting natural language questions into SQL queries, executing them safely, and interpreting results into business insights.

## ✨ Key Features

- **Natural Language Querying**: Ask questions in plain English.
- **Intelligent SQL Generation**: Advanced prompt engineering for JOINs, aggregations, and complex logic.
- **Multi-Source Config**: Manage multiple database connections via `config/sources.yaml`.
- **RAG Integration**: Query unstructured documentation and policies via ChromaDB.
- **Autonomous Error Correction**: Self-healing query execution with LLM-powered feedback loops.
- **Safe Execution**: Strict validation classes for every SQL dialect (Postgres, MySQL, Redshift, BigQuery, etc.).
- **NoSQL Support**: Query DynamoDB using PartiQL with automatic complexity validation.
- **Result Interpretation**: Transform raw data into actionable insights using rich context.
- **Modular Architecture**: Pluggable connectors, LLMs (Gemini, Anthropic, OpenAI), and vector stores.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Application Layer                   │
│  ┌──────────────┐         ┌──────────────────────┐  │
│  │  Streamlit   │         │     FastAPI          │  │
│  │     UI       │         │       API            │  │
│  └──────┬───────┘         └──────┬───────────────┘  │
└─────────┼────────────────────────┼──────────────────┘
          │                        │
┌─────────▼────────────────────────▼──────────────────┐
│           Orchestration Layer                       │
│  ┌──────────────────────────────────────────────┐   │
│  │         Query Orchestrator                   │   │
│  │  • Context Building                          │   │
│  │  • SQL Generation                            │   │
│  │  • Validation & Execution                    │   │
│  │  • Result Interpretation                     │   │
│  │  • Caching (Redis) & Metrics                 │   │
│  └──────────────────────────────────────────────┘   │
└─────────┬────────────────────────┬──────────────────┘
          │                        │
    ┌─────▼──────┐          ┌──────▼─────────┐
    │   LLM      │          │   Connector    │
    │  Provider  │          │     Layer      │
    │            │          │                │
    │  OpenAI    │          │  Postgres/MySQL│
    │ Anthropic  │          │   BigQuery     │
    │  Gemini    │          │   Redshift     │
    │  Ollama    │          │   DynamoDB     │
    └────────────┘          └────────────────┘

┌─────────────────────────────────────────────────────┐
│                 Observability Stack                 │
│  ┌──────────────┐   ┌────────────┐   ┌───────────┐  │
│  │  Prometheus  │←──│  Metrics   │   │  Grafana  │  │
│  └──────────────┘   └────────────┘   └───────────┘  │
└─────────────────────────────────────────────────────┘
```

> [!TIP]
> View the detailed visual flow in [FLOW_DIAGRAM.mermaid](file:///home/sumit/workspace/datachat/docs/FLOW_DIAGRAM.mermaid).

## 📋 Prerequisites

- Docker & Docker Compose
- OpenAI API Key (or other LLM provider key)

## 🚀 Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd genai-data-platform

# Create .env file
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` and add your API keys:

```bash
OPENAI_API_KEY=sk-...your-key-here...
# Database credentials if using external DB (optional for testing)
```

### 3. Run with Docker Compose

The easiest way to run the full platform (API, UI, Redis, Prometheus, Grafana) is via Docker:

```bash
docker-compose up --build
```

### 4. Access the Platform

- **Streamlit UI**: `http://localhost:8501`
  - **Login**: `admin` / `admin` (Default mock credentials)
- **FastAPI Docs**: `http://localhost:8000/docs`
- **Grafana Dashboards**: `http://localhost:3000` (Default: `admin` / `admin`)
- **Prometheus**: `http://localhost:9090`

### 5. Manual Setup (Dev Mode)

If you prefer running locally without Docker:

```bash
# Create venv
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis (Required)
docker run -d -p 6379:6379 redis:alpine

# Start API
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Start UI (New Terminal)
streamlit run src/ui/streamlit_app.py
```

## 💡 Usage Examples

### Using the Chat UI

1. Open the Streamlit UI at `http://localhost:8501`
2. View the database schema in the sidebar
3. Ask questions in natural language:
   - "What are the top 5 customers by total order amount?"
   - "Show me monthly sales trends"
   - "Which region has the most customers?"
4. View the generated SQL, results, and interpretation

### Using the API

```python
import requests

# Ask a question
response = requests.post(
    'http://localhost:8000/api/query',
    json={'question': 'What is the average order value?'}
)

result = response.json()
print(f"SQL Generated: {result['sql_generated']}")
print(f"Interpretation: {result['interpretation']}")
print(f"Data: {result['data']}")
```

### Using cURL

```bash
# Health check
curl http://localhost:8000/api/health

# Get schema
curl http://localhost:8000/api/schema

# Execute query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top customers by revenue?"}'
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_connectors.py
```

## 📁 Project Structure

```
genai-data-platform/
├── src/
│   ├── connectors/          # Data source connectors
│   │   ├── base.py          # Base connector interface
│   │   └── postgresql.py    # PostgreSQL implementation
│   ├── llm/                 # LLM providers
│   │   ├── base.py          # Base LLM interface
│   │   └── openai_provider.py
│   ├── rag/                 # RAG components (Stage 2)
│   ├── orchestration/       # Core orchestration logic
│   │   └── query_orchestrator.py
│   ├── api/                 # FastAPI application
│   │   └── main.py
│   └── ui/                  # User interfaces
│       └── streamlit_app.py
├── tests/                   # Test suite
├── data/                    # Data files (vector indices, etc.)
├── config/                  # Configuration files
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── docs/                   # Documentation folder
│   ├── ARCHITECTURE.md     # Detailed architecture docs
│   ├── ARCHITECTURE_VISUAL.md
│   ├── GETTING_STARTED.md
│   ├── PROJECT_CHECKLIST.md
│   └── INDEX.md
└── README.md               # This file
```

## 🔧 Configuration

### LLM Provider Selection

Edit `.env` to use different models:

```bash
# OpenAI
LLM_MODEL=gpt-4                # More accurate but expensive
LLM_MODEL=gpt-3.5-turbo        # Faster and cheaper

# Temperature (0.0 = deterministic, 1.0 = creative)
LLM_TEMPERATURE=0.1
```

### Database Configuration

```bash
DB_HOST=localhost              # Database host
DB_PORT=5432                   # Database port
DB_NAME=analytics              # Database name
DB_USER=postgres               # Username
DB_PASSWORD=your_password      # Password
DB_SCHEMA=public              # Schema to query
```

## 🛠️ Development Roadmap

### ✅ Stage 1: Foundation
- [x] PostgreSQL & SQLite connectors
- [x] OpenAI, Gemini & Anthropic LLM integration
- [x] Basic SQL generation
- [x] Query execution with validation
- [x] FastAPI endpoints
- [x] Streamlit UI

### ✅ Stage 2: SQL Optimization & Self-Correction
- [x] Advanced prompt engineering (few-shot, JOIN logic)
- [x] Schema enrichment with distinct categorical values
- [x] Autonomous SQL error correction loop
- [x] Exponential backoff for API rate limits

### ✅ Stage 3: RAG Implementation
- [x] Document ingestion pipeline (Markdown)
- [x] Vector store integration (ChromaDB)
- [x] Intent routing (SQL vs. Knowledge Base)
- [x] Retrieval-Augmented Generation for policy queries

### ✅ Stage 4: Enterprise Expansion
- [x] MySQL & SQLite connectors
- [x] BigQuery & Redshift connectors
- [x] DynamoDB (NoSQL) support
- [x] Global constant centralization for enterprise safety
- [x] Multi-source YAML configuration with env substitution

### ✅ Stage 5: Production Readiness
- [x] Authentication & RBAC
- [x] Query caching layer (Redis)
- [x] Performance monitoring with Prometheus/Grafana
- [ ] Advanced result visualization (Charts/Graphs)

## 🐛 Troubleshooting

### Common Issues

**API won't start:**
- Check if port 8000 is available: `lsof -i :8000`
- Verify environment variables are set: `cat .env`
- Check database connection: `psql -h localhost -U postgres`

**LLM errors:**
- Verify OpenAI API key is valid
- Check API quota and billing
- Ensure internet connectivity

**Database connection errors:**
- Verify PostgreSQL is running: `pg_isready`
- Check credentials in `.env`
- Test connection: `psql -h localhost -U postgres -d analytics`

**Empty/incorrect SQL generation:**
- Check database schema is accessible
- Verify tables have data
- Try rephrasing the question
- Check LLM model configuration

## 📊 Performance Considerations

- **SQL Generation**: ~2-5 seconds per query (depends on LLM)
- **Query Execution**: Varies by query complexity
- **Token Usage**: ~500-2000 tokens per query
- **Cost**: ~$0.002-0.01 per query (GPT-3.5 Turbo)

## 🔒 Security

- Only SELECT queries are allowed by default
- SQL injection prevention through validation
- Parameterized queries where possible
- Row limits automatically applied
- Query timeout controls

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📧 Support

For questions or issues:
- Check the documentation in `/docs`
- Review the architecture guide: `ARCHITECTURE.md`
- Open an issue on GitHub

## 🙏 Acknowledgments

Built with:
- FastAPI - Web framework
- LangChain - LLM orchestration
- OpenAI - Language models
- Streamlit - UI framework
- PostgreSQL - Database

---

**Happy Querying! 🚀**
