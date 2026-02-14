import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.orchestration.query_orchestrator import QueryOrchestrator

class TestQueryOrchestrator:
    def test_init(self):
        mock_connector = MagicMock()
        mock_llm = MagicMock()
        mock_llm.config.max_retries = 3
        
        orchestrator = QueryOrchestrator(
            connector=mock_connector,
            llm_provider=mock_llm
        )
        assert orchestrator.connector == mock_connector
        assert orchestrator.llm == mock_llm
