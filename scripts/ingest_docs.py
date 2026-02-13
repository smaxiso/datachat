"""
Script to ingest documents into the Knowledge Base (Vector Store).
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from loguru import logger

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("DEBUG: Ingest script started")
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStore
from src.rag.ingester import DocumentIngester

def ingest_docs(docs_dir: str):
    print(f"DEBUG: ingest_docs called with {docs_dir}")
    load_dotenv()
    
    logger.info(f"Starting ingestion from: {docs_dir}")
    
    # Initialize components
    try:
        embeddings = EmbeddingService()
        vector_store = VectorStore()
        ingester = DocumentIngester(embeddings, vector_store)
        
        # Run ingestion
        success = ingester.ingest(docs_dir)
        
        if success:
            logger.success("✅ Ingestion completed successfully")
            count = vector_store.count()
            logger.info(f"Total documents in vector store: {count}")
        else:
            logger.error("❌ Ingestion failed")
            
    except Exception as e:
        logger.error(f"Ingestion error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents into RAG system")
    parser.add_argument("--dir", default="data/docs", help="Directory containing documents")
    args = parser.parse_args()
    
    ingest_docs(args.dir)
