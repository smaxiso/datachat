import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
import shutil
import tempfile
from src.rag.vector_store import VectorStore

class TestVectorStore:
    def setup_method(self):
        self.persist_dir = tempfile.mkdtemp()
        self.store = VectorStore(persist_dir=self.persist_dir)

    def teardown_method(self):
        shutil.rmtree(self.persist_dir)

    def test_add_documents(self):
        docs = ["doc 1", "doc 2"]
        metas = [{"id": 1}, {"id": 2}]
        # Mock embeddings (384 for MiniLM)
        embeddings = [[0.1] * 384, [0.2] * 384]
        self.store.add_documents(docs, metas, embeddings)
        assert self.store.count() == 2
