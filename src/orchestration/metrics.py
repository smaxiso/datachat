"""
Metrics collection and management.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time

@dataclass
class QueryMetrics:
    """Metrics for tracking query performance and usage."""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    query_times: List[float] = field(default_factory=list)
    
    def record_query(self, success: bool, tokens: Optional[int] = None, cost: Optional[float] = None, time_seconds: float = 0.0):
        """Record metrics for a single query."""
        self.total_queries += 1
        if success:
            self.successful_queries += 1
        else:
            self.failed_queries += 1
            
        if tokens:
            self.total_tokens += tokens
        if cost:
            self.total_cost += cost
        
        self.query_times.append(time_seconds)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of metrics."""
        if self.total_queries == 0:
            return {
                "total_queries": 0,
                "success_rate": "0.0%",
                "avg_query_time": "0.00s",
                "total_tokens": 0,
                "total_cost": "$0.0000"
            }
            
        success_rate = (self.successful_queries / self.total_queries) * 100
        avg_time = sum(self.query_times) / len(self.query_times)
        
        return {
            "total_queries": self.total_queries,
            "success_rate": f"{success_rate:.1f}%",
            "avg_query_time": f"{avg_time:.2f}s",
            "total_tokens": self.total_tokens,
            "total_cost": f"${self.total_cost:.4f}",
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries
        }
