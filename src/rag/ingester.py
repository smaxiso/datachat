"""
Document ingestion pipeline for RAG.
"""

import os
import glob
from typing import List, Dict, Any
from loguru import logger

from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStore

class DocumentIngester:
    """Ingest documents into the vector store."""
    
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore):
        """
        Initialize ingester.
        
        Args:
            embedding_service: Service to generate embeddings
            vector_store: Store to save vectors
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        
    def load_documents(self, directory: str, extension: str = "**/*.md") -> List[Dict[str, Any]]:
        """
        Load documents from a directory.
        
        Args:
            directory: Root directory to search
            extension: File extension pattern (default: recursive markdown)
            
        Returns:
            List of dicts with 'content' and 'metadata'
        """
        docs = []
        search_path = os.path.join(directory, extension)
        
        logger.info(f"Searching for documents in: {search_path}")
        files = glob.glob(search_path, recursive=True)
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                docs.append({
                    "content": content,
                    "metadata": {
                        "source": file_path,
                        "filename": os.path.basename(file_path)
                    }
                })
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")
                
        logger.info(f"Loaded {len(docs)} documents")
        return docs
        
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text: Text to split
            chunk_size: Maximum characters per chunk
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = start + chunk_size
            
            # If we're not at the end of the text, try to find a natural break
            if end < text_len:
                # Look for the last newline in the chunk
                last_newline = text.rfind('\n', start, end)
                if last_newline != -1:
                    end = last_newline + 1
                else:
                    # Look for the last space
                    last_space = text.rfind(' ', start, end)
                    if last_space != -1:
                        end = last_space + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
                
            start = end - overlap
            
        return chunks
        
    def ingest(self, directory: str) -> bool:
        """
        Run full ingestion process.
        
        Args:
            directory: Directory to ingest
            
        Returns:
            Success status
        """
        # 1. Load Documents
        raw_docs = self.load_documents(directory)
        if not raw_docs:
            logger.warning("No documents found to ingest")
            return False
            
        # 2. Chunk Documents
        chunked_docs = []
        metadatas = []
        
        for doc in raw_docs:
            chunks = self.chunk_text(doc['content'])
            for i, chunk in enumerate(chunks):
                chunked_docs.append(chunk)
                
                # Copy metadata and add chunk info
                meta = doc['metadata'].copy()
                meta['chunk_id'] = i
                metadatas.append(meta)
                
        logger.info(f"Created {len(chunked_docs)} chunks from {len(raw_docs)} files")
        
        if not chunked_docs:
            return False
            
        # 3. Generate Embeddings
        logger.info("Generating embeddings...")
        embeddings = self.embedding_service.generate_embeddings(chunked_docs)
        
        if not embeddings:
            logger.error("Failed to generate embeddings")
            return False
            
        # 4. Store in Vector DB
        logger.info("Storing in Vector DB...")
        success = self.vector_store.add_documents(
            documents=chunked_docs,
            metadatas=metadatas,
            embeddings=embeddings
        )
        
        return success
