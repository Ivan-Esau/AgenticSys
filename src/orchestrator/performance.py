"""
Performance tracking for agent orchestration.
Provides essential metrics without unnecessary complexity.
"""

import time
from typing import Dict, Any, Optional


class PerformanceTracker:
    """Track agent performance metrics and timing."""
    
    def __init__(self):
        self.metrics = {}
        self.active_timings = {}
    
    def start_task_timing(self, agent_name: str, task_type: str) -> str:
        """Start timing a task execution."""
        timing_id = f"{agent_name}_{task_type}_{int(time.time() * 1000)}"
        self.active_timings[timing_id] = {
            "agent": agent_name,
            "start_time": time.time()
        }
        return timing_id
    
    def end_task_timing(self, timing_id: str, success: bool = True, error: Optional[str] = None):
        """Complete timing for a task execution."""
        if timing_id not in self.active_timings:
            return
        
        timing_data = self.active_timings.pop(timing_id)
        agent_name = timing_data["agent"]
        duration = time.time() - timing_data["start_time"]
        
        # Initialize metrics for agent if needed
        if agent_name not in self.metrics:
            self.metrics[agent_name] = {
                "calls": 0,
                "errors": 0,
                "total_time": 0.0
            }
        
        # Update metrics
        self.metrics[agent_name]["calls"] += 1
        self.metrics[agent_name]["total_time"] += duration
        if not success:
            self.metrics[agent_name]["errors"] += 1
    
    def get_performance_summary(self) -> str:
        """Get a performance summary string."""
        if not self.metrics:
            return "No performance data available"
        
        summary_parts = []
        for agent_name, data in self.metrics.items():
            if data["calls"] == 0:
                continue
            
            success_rate = ((data["calls"] - data["errors"]) / data["calls"]) * 100
            avg_time = data["total_time"] / data["calls"]
            
            summary_parts.append(
                f"{agent_name}: {data['calls']} calls, "
                f"{success_rate:.1f}% success rate, "
                f"{avg_time:.1f}s avg time"
            )
        
        return "; ".join(summary_parts) if summary_parts else "No performance data"