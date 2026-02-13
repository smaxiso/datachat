import os
import sys
import argparse
import traceback
from dotenv import load_dotenv
from loguru import logger

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.connectors.factory import ConnectorFactory
from src.llm.factory import LLMFactory
from src.orchestration.query_orchestrator import QueryOrchestrator, RAG_AVAILABLE

def run_rag_tests():
    load_dotenv()
    
    logger.info("="*50)
    logger.info("Starting RAG Verification")
    logger.info("="*50)
    
    if not RAG_AVAILABLE:
        logger.error("❌ RAG dependencies are missing. Cannot run tests.")
        return

    # Initialize components
    try:
        connector = ConnectorFactory.create_connector()
        if not connector.connect():
            logger.error("Failed to connect to database")
            return
            
        llm = LLMFactory.create_provider()
        orchestrator = QueryOrchestrator(connector, llm)
        logger.success("Components initialized successfully")
        
        # Verify RAG components loaded
        if not orchestrator.vector_store or orchestrator.vector_store.count() == 0:
            logger.error("❌ Vector Store is empty or not initialized. Run ingest_docs.py first.")
            return
        
        logger.info(f"Vector Store contains {orchestrator.vector_store.count()} documents.")
        
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return

    # Test Cases
    test_cases = [
        {
            "category": "RAG Query (Policy)",
            "question": "What is the return policy for used items?",
            "expected_mode": "KNOWLEDGE_BASE"
        },
        {
            "category": "SQL Query (Data)",
            "question": "How many total orders are there?",
            "expected_mode": "SQL_DATA"
        },
        {
            "category": "RAG Query (Shipping)",
            "question": "How long does express shipping take?",
            "expected_mode": "KNOWLEDGE_BASE"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['category']}", flush=True)
        print(f"Question: {test['question']}", flush=True)
        
        try:
            # We can't easily check the internal intent without mocking, 
            # but we can check the response metadata
            response = orchestrator.process_question(test['question'])
            
            if response.success:
                logger.success("✅ Query processed successfully")
                
                is_rag = response.metadata and response.metadata.get('rag_mode', False)
                mode = "KNOWLEDGE_BASE" if is_rag else "SQL_DATA"
                
                print(f"   Detected Mode: {mode}", flush=True)
                
                if mode == test['expected_mode']:
                    print(f"   ✅ Correctly routed to {mode}", flush=True)
                    print(f"   Answer/Interpretation: {response.interpretation}", flush=True)
                    results.append({"id": i, "status": "PASS", "msg": "Success"})
                else:
                    print(f"   ❌ Incorrect routing. Expected {test['expected_mode']}, got {mode}", flush=True)
                    results.append({"id": i, "status": "FAIL", "msg": f"Wrong Routing: {mode}"})
                     
            else:
                print(f"❌ Failed: {response.error_message}", flush=True)
                results.append({"id": i, "status": "FAIL", "msg": response.error_message})
                
        except Exception as e:
            print(f"❌ Exception: {e}", flush=True)
            results.append({"id": i, "status": "ERROR", "msg": str(e)})
            
    # Summary
    print("\n" + "="*50, flush=True)
    print("Test Summary", flush=True)
    print("="*50, flush=True)
    for res in results:
        icon = "✅" if res['status'] == 'PASS' else "❌"
        print(f"{icon} Test {res['id']}: {res['status']} - {res['msg']}", flush=True)

if __name__ == "__main__":
    try:
        run_rag_tests()
    except Exception as e:
        print("CRITICAL ERROR IN test_rag.py")
        traceback.print_exc()
        sys.exit(1)
