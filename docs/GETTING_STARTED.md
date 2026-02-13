# DataChat - Getting Started Guide

## 📦 What You Have

This starter kit contains a complete, working implementation of a GenAI-powered data intelligence platform (Stage 1). Here's what's included:

### Core Components

1. **Data Connector Layer** (`src/connectors/`)
   - `base.py` - Abstract connector interface
   - `postgresql.py` - Full PostgreSQL implementation with safety features
   - Includes query validation, execution controls, and schema discovery

2. **LLM Engine Layer** (`src/llm/`)
   - `base.py` - Abstract LLM provider interface
   - `openai_provider.py` - OpenAI GPT integration
   - Handles SQL generation, query refinement, and result interpretation

3. **Orchestration Layer** (`src/orchestration/`)
   - `query_orchestrator.py` - Core intelligence that coordinates all components
   - Implements the complete query processing workflow
   - Includes retry logic and error handling

4. **API Layer** (`src/api/`)
   - `main.py` - FastAPI REST API with endpoints for:
     - `/api/query` - Execute natural language queries
     - `/api/health` - System health check
     - `/api/schema` - Get database schema
     - `/api/sources` - List data sources

5. **UI Layer** (`src/ui/`)
   - `streamlit_app.py` - Interactive chat interface
   - Real-time query execution and results display
   - Schema browser and example queries

### Supporting Files

- `requirements.txt` - All Python dependencies
- `.env.example` - Environment variable template
- `ARCHITECTURE.md` - Detailed technical architecture documentation
- `README.md` - Comprehensive setup and usage guide
- `.gitignore` - Standard Python gitignore
- `scripts/setup_sample_db.py` - Create sample database with test data
- `tests/test_connectors.py` - Unit test examples
- `quick_start.sh` - Automated setup script

## 🚀 Quick Start (5 Minutes)

### Option 1: Automated Setup

```bash
# Make the script executable (if not already)
chmod +x quick_start.sh

# Run the setup
./quick_start.sh
```

This script will:
1. Create virtual environment
2. Install dependencies
3. Set up .env file
4. Optionally create sample database

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Create sample database (optional)
python scripts/setup_sample_db.py

# 5. Start API server
cd src/api
python -m uvicorn main:app --reload

# 6. Start UI (new terminal)
source venv/bin/activate
cd src/ui
streamlit run streamlit_app.py
```

## 🔑 Required Configuration

Before starting, you must configure these in `.env`:

```bash
# Database - Required
DB_HOST=localhost
DB_NAME=analytics
DB_USER=postgres
DB_PASSWORD=your_password

# OpenAI - Required
OPENAI_API_KEY=sk-...your-key-here...

# Optional - Use defaults or customize
LLM_MODEL=gpt-3.5-turbo  # or gpt-4
LLM_TEMPERATURE=0.1
```

## 💡 Example Usage

Once running, you can ask questions like:

### Business Analytics
- "What are the top 5 customers by total revenue?"
- "Show me sales trends by month for 2024"
- "Which product category generates the most profit?"
- "Compare revenue across different regions"

### Data Exploration
- "How many orders were placed last week?"
- "What is the average order value?"
- "Which products have the lowest stock?"
- "Show me customer signup trends"

### Complex Queries
- "Find customers who haven't ordered in the last 30 days"
- "Calculate profit margin by product category"
- "Show regional performance with year-over-year growth"

## 📊 Architecture Overview

```
User Question
     ↓
[Streamlit UI / API]
     ↓
[Query Orchestrator]
     ↓
   ┌─────────────┬─────────────┐
   ↓             ↓             ↓
[Schema]    [LLM: SQL]    [Execute]
Context    Generation     Query
   ↓             ↓             ↓
   └─────────────┴─────────────┘
                ↓
        [Interpret Results]
                ↓
          User Response
```

## 🎯 What's Working

### ✅ Currently Functional

- **Natural Language to SQL**: Convert questions to SQL queries
- **Safe Execution**: Validation prevents destructive operations
- **Auto Retry**: Failed queries automatically refined
- **Result Interpretation**: LLM explains results in plain language
- **Schema Discovery**: Automatic metadata extraction
- **REST API**: Full FastAPI implementation
- **Chat UI**: Interactive Streamlit interface
- **Multiple Endpoints**: Query, health, schema APIs

### 🔧 Production-Ready Features

- Query validation and safety controls
- Automatic LIMIT clause injection
- SQL injection prevention
- Timeout controls
- Error handling and retry logic
- Structured logging
- Connection pooling
- Type safety with Pydantic

## 📈 Next Steps (Stages 2-5)

### Stage 2: RAG Implementation
Add vector database for smarter context retrieval:
- Index schema metadata
- Semantic search for relevant tables
- Improve SQL accuracy
- Reduce token usage

### Stage 3: Multi-Provider Support
Add flexibility:
- Support Anthropic Claude, local Ollama
- Multiple vector stores (Pinecone, Chroma)
- Configuration-driven selection

### Stage 4: Multi-Source
Expand data access:
- MySQL, BigQuery, Snowflake connectors
- Cross-database queries
- Unified metadata layer

### Stage 5: Production Features
Enterprise readiness:
- Authentication & authorization
- Query caching and history
- Cost tracking and optimization
- Monitoring dashboards
- Advanced error recovery

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_connectors.py -v
```

## 📝 Key Files to Understand

1. **src/orchestration/query_orchestrator.py**
   - Main workflow logic
   - Study this to understand the query pipeline

2. **src/llm/openai_provider.py**
   - Prompt engineering examples
   - LLM interaction patterns

3. **src/connectors/postgresql.py**
   - Safety and validation logic
   - Schema extraction

4. **src/api/main.py**
   - API endpoint definitions
   - Request/response models

## 🐛 Common Issues

**"Module not found" errors:**
```bash
# Make sure you're in the right directory and venv is activated
source venv/bin/activate
pip install -r requirements.txt
```

**Database connection fails:**
```bash
# Test PostgreSQL connection
psql -h localhost -U postgres -d analytics
# If this fails, check PostgreSQL is running
```

**API won't start:**
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill process or use different port
```

**OpenAI errors:**
- Verify API key is correct
- Check you have API credits
- Try reducing LLM_MAX_TOKENS if hitting limits

## 💰 Cost Estimate

Using GPT-3.5-turbo:
- ~$0.002 per query
- $1 ≈ 500 queries
- GPT-4 is ~15x more expensive but more accurate

## 🎓 Learning Path

1. **Day 1**: Get it running
   - Complete quick start
   - Try example queries
   - Explore the UI

2. **Day 2**: Understand the code
   - Read ARCHITECTURE.md
   - Study query_orchestrator.py
   - Trace a query through the system

3. **Day 3**: Customize
   - Add your own database
   - Modify prompts in openai_provider.py
   - Add custom validation rules

4. **Day 4**: Extend
   - Start implementing Stage 2 (RAG)
   - Add new connector (MySQL)
   - Improve error handling

## 📚 Documentation

- `README.md` - Setup and usage
- `ARCHITECTURE.md` - Technical architecture
- `/docs` API documentation at `http://localhost:8000/docs`
- Inline code comments throughout

## 🤝 Support

- Check `/docs` for detailed documentation
- Review code comments for implementation details
- Study test files for usage examples

## 🎉 You're Ready!

You now have a fully functional GenAI data intelligence platform. Start by:

1. Running the quick_start.sh script
2. Opening the UI at localhost:8501
3. Asking your first question!

Happy querying! 🚀
