import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock
from src.rag.ingester import DocumentIngester

class TestDocumentIngester:
    def test_init(self):
         mock_emb = MagicMock()
         mock_vec = MagicMock()
         ingester = DocumentIngester(mock_emb, mock_vec)
         assert ingester is not None
