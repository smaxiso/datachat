#!/bin/bash

# Quick Start Script for DataChat
# This script helps you get started quickly

echo "=================================================="
echo "DataChat - Quick Start"
echo "=================================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL client not found. Make sure PostgreSQL is installed."
fi

echo ""
echo "Step 1: Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo ""
echo "Step 2: Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Step 3: Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "⚠️  IMPORTANT: Edit .env and add your credentials:"
    echo "   - OpenAI API Key"
    echo "   - Database credentials"
    echo ""
    read -p "Press Enter when you've updated .env file..."
else
    echo "✅ .env file already exists"
fi

echo ""
echo "Step 4: Setting up sample database (optional)..."
read -p "Do you want to create a sample database with test data? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python scripts/setup_sample_db.py
fi

echo ""
echo "=================================================="
echo "Setup Complete! 🎉"
echo "=================================================="
echo ""
echo "To start the platform:"
echo ""
echo "1. Start the API server:"
echo "   cd src/api && python -m uvicorn main:app --reload"
echo ""
echo "2. Start the UI (in a new terminal):"
echo "   source venv/bin/activate"
echo "   cd src/ui && streamlit run streamlit_app.py"
echo ""
echo "3. Access the application:"
echo "   - API: http://localhost:8000"
echo "   - UI:  http://localhost:8501"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "=================================================="
