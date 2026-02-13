"""
Test script for complex SQL generation and self-correction.
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from loguru import logger

import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.connectors.factory import ConnectorFactory
from src.llm.factory import LLMFactory
from src.orchestration.query_orchestrator import QueryOrchestrator

def run_complex_tests(skip_llm=False):
    load_dotenv()
    
    logger.info("="*50)
    logger.info("Starting Complex Query Verification")
    logger.info("="*50)
    
    # Initialize components
    try:
        connector = ConnectorFactory.create_connector()
        if not connector.connect():
            logger.error("Failed to connect to database")
            return
            
        llm = LLMFactory.create_provider()
        orchestrator = QueryOrchestrator(connector, llm)
        logger.success("Components initialized successfully")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return

    # Test Cases
    test_cases = [
        {
            "category": "Basic Aggregation",
            "question": "How many total orders are there?",
            "expected_keywords": ["COUNT", "orders"]
        },
        {
            "category": "Categorical Filter (Schema Enrichment)",
            "question": "How many orders have 'completed' status?",
            "expected_keywords": ["WHERE", "status", "'completed'"]
        },
        {
            "category": "JOIN Operation",
            "question": "What is the total revenue from customers in the 'North' region?",
            "expected_keywords": ["JOIN", "customers", "orders", "SUM(total_amount)", "North"]
        },
        {
            "category": "Date Logic",
            "question": "How many customers signed up in 2023?",
            "expected_keywords": ["customers", "2023", "signup_date"]
        },
        {
            "category": "Complex Multi-table",
            "question": "List all products bought by 'John Doe'.",
            "expected_keywords": ["products", "order_items", "orders", "customers", "John Doe"]
        },
        {
            "category": "Self-Correction (Intentional Error)",
            "question": "Count the number of users", # 'users' table doesn't exist, should map to 'customers'
            "expected_keywords": ["customers", "COUNT"]
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['category']}", flush=True)
        print(f"Question: {test['question']}", flush=True)
        
        try:
            response = orchestrator.process_question(test['question'])
            
            if response.success:
                print("✅ Query processed successfully", flush=True)
                print(f"   SQL: {response.sql_generated}", flush=True)
                
                # Basic validation
                sql_upper = response.sql_generated.upper()
                missing_keywords = [k for k in test['expected_keywords'] if k.upper().replace("'", "").replace("(", "").replace(")", "") not in sql_upper.replace("'", "").replace("(", "").replace(")", "")]
                
                if missing_keywords:
                    print(f"   ⚠️ Potential issue: Missing keywords {missing_keywords}", flush=True)
                    results.append({"id": i, "status": "WARN", "msg": f"Missing components: {missing_keywords}"})
                else:
                    results.append({"id": i, "status": "PASS", "msg": "Success"})
                    
                if response.data is not None and not response.data.empty:
                     print(f"   Rows returned: {len(response.data)}", flush=True)
                else:
                     print("   ⚠️ No data returned (might be valid depending on data)", flush=True)
                     
            else:
                print(f"❌ Failed: {response.error_message}", flush=True)
                results.append({"id": i, "status": "FAIL", "msg": response.error_message})
                
        except Exception as e:
            print(f"❌ Exception: {e}", flush=True)
            results.append({"id": i, "status": "ERROR", "msg": str(e)})
            
            results.append({"id": i, "status": "ERROR", "msg": str(e)})
            
    # Summary
    logger.info("\n" + "="*50)
    logger.info("Test Summary")
    logger.info("="*50)
    for res in results:
        icon = "✅" if res['status'] == 'PASS' else "⚠️" if res['status'] == 'WARN' else "❌"
        logger.info(f"{icon} Test {res['id']}: {res['status']} - {res['msg']}")

if __name__ == "__main__":
    run_complex_tests()
