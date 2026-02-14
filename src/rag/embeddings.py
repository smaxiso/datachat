"""
Embeddings generation using SentenceTransformers.
"""

import os
from typing import List, Optional
from loguru import logger
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    logger.warning("sentence-transformers not installed. RAG features will not work.")
    SentenceTransformer = None

from src.utils.constants import RAGConstants

class EmbeddingService:
    """Service to generate embeddings for text."""
    
    def __init__(self, model_name: str = RAGConstants.EMBEDDING_MODEL):
        """
        Initialize embedding model.
        
        Args:
            model_name: Name of the sentence-transformer model
        """
        self.model_name = model_name
        self.model = None
        self._initialize_model()
        
    def _initialize_model(self):
        """Lazy load the model."""
        if SentenceTransformer is None or os.environ.get("USE_MOCK_EMBEDDINGS") == "1":
            logger.warning("Using Mock Embedding Service (Random Vectors)")
            self.model = "MOCK"
            return

        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.success("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        """
        if not self.model:
            self._initialize_model()
            
        if self.model == "MOCK":
            import random
            # Return random but consistent-sized vectors (384 for MiniLM)
            return [[random.uniform(-1, 1) for _ in range(384)] for _ in texts]
            
        try:
            # Generate embeddings
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            
            # Convert numpy arrays to lists
            if hasattr(embeddings, 'tolist'):
                return embeddings.tolist()
            return [e.tolist() for e in embeddings]
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return []
            
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        result = self.generate_embeddings([text])
        return result[0] if result else None
