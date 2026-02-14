# DataChat

A modular, RAG-powered GenAI platform that enables natural language querying across multiple data sources.

## 🎯 Overview

This platform acts as an intelligent interface layer between users and data infrastructure, converting natural language questions into SQL queries, executing them safely, and interpreting results into business insights.

## ✨ Key Features

- **Natural Language Querying**: Ask questions in plain English.
- **Intelligent SQL Generation**: Advanced prompt engineering for JOINs, aggregations, and complex logic.
- **RAG Integration**: Query unstructured documentation and policies via ChromaDB.
- **Autonomous Error Correction**: Self-healing query execution with LLM-powered feedback loops.
- **Safe Execution**: Validation and safety controls for query execution.
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
│  └──────────────────────────────────────────────┘   │
└─────────┬────────────────────────┬──────────────────┘
          │                        │
    ┌─────▼──────┐          ┌──────▼─────────┐
    │   LLM      │          │   Connector    │
    │  Provider  │          │     Layer      │
    │            │          │                │
    │  OpenAI    │          │  PostgreSQL    │
    │ Anthropic  │          │    MySQL       │
    │  Ollama    │          │  BigQuery      │
    └────────────┘          └────────────────┘
```

## 📋 Prerequisites

- Python 3.10 or higher
- PostgreSQL database (or other supported database)
- OpenAI API key (or other LLM provider)
- 4GB+ RAM recommended

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd genai-data-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

Required configurations in `.env`:
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database credentials
- `OPENAI_API_KEY` - Your OpenAI API key
- Optional: Adjust `LLM_MODEL`, `LLM_TEMPERATURE`, etc.

### 3. Prepare Database

Ensure you have a PostgreSQL database with some data. Example schema:

```sql
-- Example: Create a sample analytics database
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    region VARCHAR(50)
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_date DATE,
    total_amount DECIMAL(10,2)
);

-- Insert sample data
INSERT INTO customers (name, email, region) VALUES
    ('John Doe', 'john@example.com', 'North'),
    ('Jane Smith', 'jane@example.com', 'South');

INSERT INTO orders (customer_id, order_date, total_amount) VALUES
    (1, '2024-01-15', 150.00),
    (2, '2024-01-20', 200.00);
```

### 4. Start the API Server

```bash
# From project root
cd src/api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### 5. Start the UI (Optional)

In a new terminal:

### 5. Start with docs/GETTING_STARTED.md and you'll be up and running in minutes!al:

```bash
# Activate virtual environment
source venv/bin/activate

# Start Streamlit
cd src/ui
streamlit run streamlit_app.py
```

UI will be available at: `http://localhost:8501`

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

### 📅 Stage 4: Multi-Source Support
- [x] MySQL connector (Ready for implementation)
- [ ] BigQuery connector (Planned)
- [ ] Cross-database query orchestration
- [ ] Unified metadata schema management

### 📅 Stage 5: Production Features
- [ ] Authentication & authorization
- [ ] Query history and caching
- [ ] Performance optimization
- [ ] Advanced error handling
- [ ] Monitoring and observability

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
