"""
Verification script for DataChat setup.

This script checks:
1. Environment variables
2. Database connection
3. LLM provider connection
4. Simple query workflow
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from loguru import logger

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.connectors.factory import ConnectorFactory
from src.llm.factory import LLMFactory
from src.orchestration.query_orchestrator import QueryOrchestrator


def verify_setup(skip_llm=False):
    """Run verification checks."""
    load_dotenv()
    
    logger.info("="*50)
    logger.info("Starting DataChat Verification")
    logger.info("="*50)
    
    # 1. Check Database
    logger.info("\n1. Checking Database Connection...")
    
    try:
        connector = ConnectorFactory.create_connector()
        if connector.connect():
            logger.success(f"✅ Database connected successfully ({os.getenv('DB_TYPE', 'postgres')})")
            
            # Verify schema
            try:
                schema = connector.get_schema()
                table_count = len(schema.tables)
                logger.info(f"   Found {table_count} tables: {', '.join([t.name for t in schema.tables])}")
                if table_count == 0:
                    logger.warning("   ⚠️ Database connected but no tables found. Did you run setup_sample_db.py?")
            except Exception as e:
                logger.error(f"   ❌ Failed to retrieve schema: {e}")
                
        else:
            logger.error("❌ Database connection failed")
            return False
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False
        
    if skip_llm:
        logger.info("\nSkipping LLM verification as requested.")
        return True

    # 2. Check LLM Provider
    logger.info("\n2. Checking LLM Provider...")
    provider_name = os.getenv('LLM_PROVIDER', 'openai')
    logger.info(f"   Configured provider: {provider_name}")
    
    try:
        llm = LLMFactory.create_provider()
        logger.success(f"✅ LLM Provider ({provider_name}) initialized")
    except Exception as e:
        logger.error(f"❌ LLM initialization failed: {e}")
        logger.info("   Check your API keys in .env")
        return False
        
    # 3. Test End-to-End Flow
    logger.info("\n3. Testing Query Workflow...")
    orchestrator = QueryOrchestrator(connector, llm)
    
    test_question = "How many customers are there?"
    logger.info(f"   Question: {test_question}")
    
    try:
        response = orchestrator.process_question(test_question)
        
        if response.success:
            logger.success("✅ Query processed successfully")
            logger.info(f"   SQL: {response.sql_generated}")
            logger.info(f"   Answer: {response.interpretation}")
        else:
            logger.error(f"❌ Query processing failed: {response.error_message}")
            if response.sql_generated:
                logger.info(f"   Generated SQL: {response.sql_generated}")
                
    except Exception as e:
        logger.error(f"❌ Unexpected error during query processing: {e}")
        return False
        
    logger.info("\n" + "="*50)
    logger.success("Verification Complete! system is ready.")
    logger.info("="*50)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify DataChat setup")
    parser.add_argument("--skip-llm", action="store_true", help="Skip LLM verification")
    args = parser.parse_args()
    
    success = verify_setup(skip_llm=args.skip_llm)
    sys.exit(0 if success else 1)
