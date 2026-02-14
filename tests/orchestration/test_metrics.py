import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from src.orchestration.metrics import QueryMetrics

class TestQueryMetrics:
    def test_init(self):
        metrics = QueryMetrics()
        assert metrics.total_queries == 0
        assert len(metrics.query_times) == 0
