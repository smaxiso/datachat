import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.rag.embeddings import EmbeddingService

class TestEmbeddingService:
    @patch('src.rag.embeddings.SentenceTransformer')
    def test_init_real(self, mock_transformer):
        service = EmbeddingService()
        assert service.model is not None

    def test_init_mock(self):
        with patch.dict(os.environ, {"USE_MOCK_EMBEDDINGS": "1"}):
            service = EmbeddingService()
            assert service.model == "MOCK"
        
    def test_embed_mock(self):
        with patch.dict(os.environ, {"USE_MOCK_EMBEDDINGS": "1"}):
            service = EmbeddingService()
            vec = service.generate_embedding("test")
            assert len(vec) == 384
