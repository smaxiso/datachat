"""
Vector Store implementation using ChromaDB.
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from loguru import logger
try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    logger.warning("chromadb not installed. RAG features will not work.")
    chromadb = None

class VectorStore:
    """Wrapper around ChromaDB for vector storage."""
    
    def __init__(self, persist_dir: str = "data/chroma", collection_name: str = "datachat_docs"):
        """
        Initialize Vector Store.
        
        Args:
            persist_dir: Directory to store ChromaDB data
            collection_name: Name of the collection
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialize_db()
        
    def _initialize_db(self):
        """Initialize ChromaDB client and collection."""
        if chromadb is None:
            logger.error("Cannot initialize VectorStore: chromadb not installed")
            return
            
        try:
            # Ensure directory exists
            if not os.path.exists(self.persist_dir):
                os.makedirs(self.persist_dir, exist_ok=True)
                
            logger.info(f"Initializing ChromaDB in {self.persist_dir}")
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            logger.success(f"Connected to collection: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            
    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]], embeddings: List[List[float]], ids: Optional[List[str]] = None) -> bool:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of text content
            metadatas: List of metadata dicts
            embeddings: List of embedding vectors
            ids: Optional list of IDs. Generated if not provided.
            
        Returns:
            dataset: Success status
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return False
            
        try:
            if not ids:
                ids = [str(uuid.uuid4()) for _ in documents]
                
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            return False
            
    def query_similar(self, query_embedding: List[float], n_results: int = 3) -> Dict[str, Any]:
        """
        Find similar documents.
        
        Args:
            query_embedding: Embedding of the query
            n_results: Number of results to return
            
        Returns:
            Dictionary with 'documents', 'metadatas', 'distances'
        """
        if not self.collection:
            logger.error("Collection not initialized")
            return {}
            
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            return results
            
        except Exception as e:
            logger.error(f"Error querying vector store: {e}")
            return {}
            
    def count(self) -> int:
        """Get document count."""
        if not self.collection:
            return 0
        return self.collection.count()
