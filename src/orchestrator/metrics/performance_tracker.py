"""
Performance tracking for the supervisor orchestrator.
Tracks agent performance metrics and statistics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import time


class PerformanceTracker:
    """
    Tracks agent performance metrics and provides analytics.
    Observer pattern - passively collects metrics without affecting operations.
    """
    
    def __init__(self):
        self.agent_metrics = {
            "planning": {"calls": 0, "errors": 0, "total_time": 0.0, "last_success": None},
            "coding": {"calls": 0, "errors": 0, "total_time": 0.0, "last_success": None},
            "testing": {"calls": 0, "errors": 0, "total_time": 0.0, "last_success": None},
            "review": {"calls": 0, "errors": 0, "total_time": 0.0, "last_success": None}
        }
        
        # Detailed execution history
        self.execution_history = []
        
        # Performance thresholds for alerts
        self.performance_thresholds = {
            "max_error_rate": 0.20,  # 20% error rate threshold
            "max_avg_time": 300.0,   # 5 minutes average execution time
            "min_success_rate": 0.80  # 80% minimum success rate
        }
    
    def start_task_timing(self, agent_name: str, task_type: str) -> str:
        """
        Start timing a task execution.
        
        Args:
            agent_name: Name of the agent
            task_type: Type of task being executed
            
        Returns:
            str: Timing ID for this task
        """
        timing_id = f"{agent_name}_{task_type}_{int(time.time() * 1000)}"
        start_time = time.time()
        
        # Record task start
        self.execution_history.append({
            "timing_id": timing_id,
            "agent": agent_name,
            "task_type": task_type,
            "start_time": start_time,
            "end_time": None,
            "success": None,
            "error": None
        })
        
        return timing_id
    
    def end_task_timing(self, timing_id: str, success: bool = True, error: Optional[str] = None):
        """
        End timing for a task execution.
        
        Args:
            timing_id: Timing ID from start_task_timing
            success: Whether the task completed successfully
            error: Error message if task failed
        """
        end_time = time.time()
        
        # Find the corresponding execution record
        for record in reversed(self.execution_history):
            if record["timing_id"] == timing_id:
                record["end_time"] = end_time
                record["success"] = success
                record["error"] = error
                
                # Update agent metrics
                agent_name = record["agent"]
                if agent_name in self.agent_metrics:
                    metrics = self.agent_metrics[agent_name]
                    metrics["calls"] += 1
                    
                    if not success:
                        metrics["errors"] += 1
                    else:
                        metrics["last_success"] = datetime.now()
                    
                    # Update total time
                    execution_time = end_time - record["start_time"]
                    metrics["total_time"] += execution_time
                
                break
    
    def record_agent_call(self, agent_name: str, success: bool = True):
        """
        Record an agent call (simplified version without detailed timing).
        
        Args:
            agent_name: Name of the agent
            success: Whether the call was successful
        """
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = {
                "calls": 0, "errors": 0, "total_time": 0.0, "last_success": None
            }
        
        metrics = self.agent_metrics[agent_name]
        metrics["calls"] += 1
        
        if not success:
            metrics["errors"] += 1
        else:
            metrics["last_success"] = datetime.now()
    
    def get_agent_metrics(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for specific agent or all agents.
        
        Args:
            agent_name: Specific agent name, or None for all agents
            
        Returns:
            Dict containing performance metrics
        """
        if agent_name:
            if agent_name not in self.agent_metrics:
                return {}
            return self._calculate_derived_metrics(agent_name, self.agent_metrics[agent_name])
        
        # Return metrics for all agents
        result = {}
        for name, metrics in self.agent_metrics.items():
            result[name] = self._calculate_derived_metrics(name, metrics)
        
        return result
    
    def _calculate_derived_metrics(self, agent_name: str, base_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived metrics from base metrics."""
        calls = base_metrics["calls"]
        errors = base_metrics["errors"]
        total_time = base_metrics["total_time"]
        
        # Calculate derived values
        error_rate = (errors / calls) if calls > 0 else 0.0
        success_rate = ((calls - errors) / calls) if calls > 0 else 1.0
        avg_time = (total_time / calls) if calls > 0 else 0.0
        
        return {
            **base_metrics,
            "error_rate": error_rate,
            "success_rate": success_rate,
            "avg_execution_time": avg_time,
            "performance_score": self._calculate_performance_score(success_rate, avg_time, calls)
        }
    
    def _calculate_performance_score(self, success_rate: float, avg_time: float, calls: int) -> float:
        """
        Calculate overall performance score (0.0 to 1.0).
        
        Args:
            success_rate: Success rate (0.0 to 1.0)
            avg_time: Average execution time in seconds
            calls: Total number of calls
            
        Returns:
            float: Performance score (0.0 to 1.0, higher is better)
        """
        if calls == 0:
            return 0.5  # Neutral score for no data
        
        # Weight factors
        success_weight = 0.6
        speed_weight = 0.3
        reliability_weight = 0.1
        
        # Success component (0.0 to 1.0)
        success_component = success_rate
        
        # Speed component (inverse of time, capped at reasonable limits)
        max_reasonable_time = 600.0  # 10 minutes
        speed_component = max(0.0, 1.0 - (avg_time / max_reasonable_time))
        
        # Reliability component (based on call count - more calls = more reliable)
        reliability_component = min(1.0, calls / 50.0)  # Full credit at 50+ calls
        
        return (
            success_component * success_weight + 
            speed_component * speed_weight + 
            reliability_component * reliability_weight
        )
    
    def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """
        Get performance alerts based on thresholds.
        
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        for agent_name, metrics in self.agent_metrics.items():
            if metrics["calls"] == 0:
                continue
            
            derived_metrics = self._calculate_derived_metrics(agent_name, metrics)
            
            # Check error rate
            if derived_metrics["error_rate"] > self.performance_thresholds["max_error_rate"]:
                alerts.append({
                    "type": "high_error_rate",
                    "agent": agent_name,
                    "value": derived_metrics["error_rate"],
                    "threshold": self.performance_thresholds["max_error_rate"],
                    "severity": "high" if derived_metrics["error_rate"] > 0.5 else "medium",
                    "message": f"{agent_name} has high error rate: {derived_metrics['error_rate']:.1%}"
                })
            
            # Check average execution time
            if derived_metrics["avg_execution_time"] > self.performance_thresholds["max_avg_time"]:
                alerts.append({
                    "type": "slow_execution",
                    "agent": agent_name,
                    "value": derived_metrics["avg_execution_time"],
                    "threshold": self.performance_thresholds["max_avg_time"],
                    "severity": "medium",
                    "message": f"{agent_name} has slow execution: {derived_metrics['avg_execution_time']:.1f}s avg"
                })
            
            # Check success rate
            if derived_metrics["success_rate"] < self.performance_thresholds["min_success_rate"]:
                alerts.append({
                    "type": "low_success_rate",
                    "agent": agent_name,
                    "value": derived_metrics["success_rate"],
                    "threshold": self.performance_thresholds["min_success_rate"],
                    "severity": "high",
                    "message": f"{agent_name} has low success rate: {derived_metrics['success_rate']:.1%}"
                })
        
        return alerts
    
    def get_execution_history(
        self, 
        agent_name: Optional[str] = None, 
        limit: Optional[int] = None,
        include_errors_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get execution history with optional filtering.
        
        Args:
            agent_name: Filter by specific agent
            limit: Maximum number of records to return
            include_errors_only: Only return failed executions
            
        Returns:
            List of execution records
        """
        filtered_history = self.execution_history
        
        # Filter by agent
        if agent_name:
            filtered_history = [h for h in filtered_history if h["agent"] == agent_name]
        
        # Filter by errors only
        if include_errors_only:
            filtered_history = [h for h in filtered_history if h["success"] is False]
        
        # Sort by start time (most recent first)
        filtered_history = sorted(filtered_history, key=lambda x: x["start_time"], reverse=True)
        
        # Apply limit
        if limit:
            filtered_history = filtered_history[:limit]
        
        return filtered_history
    
    def reset_metrics(self, agent_name: Optional[str] = None):
        """
        Reset metrics for specific agent or all agents.
        
        Args:
            agent_name: Specific agent to reset, or None for all agents
        """
        if agent_name:
            if agent_name in self.agent_metrics:
                self.agent_metrics[agent_name] = {
                    "calls": 0, "errors": 0, "total_time": 0.0, "last_success": None
                }
        else:
            # Reset all metrics
            for name in self.agent_metrics:
                self.agent_metrics[name] = {
                    "calls": 0, "errors": 0, "total_time": 0.0, "last_success": None
                }
            
            self.execution_history = []
    
    def get_performance_summary(self) -> str:
        """
        Get a human-readable performance summary string.
        
        Returns:
            str: Formatted performance summary
        """
        if not any(metrics["calls"] > 0 for metrics in self.agent_metrics.values()):
            return "No performance data available"
        
        summary_lines = []
        
        for agent_name, metrics in self.agent_metrics.items():
            if metrics["calls"] == 0:
                continue
            
            derived = self._calculate_derived_metrics(agent_name, metrics)
            
            summary_lines.append(
                f"{agent_name}: {metrics['calls']} calls, "
                f"{derived['success_rate']:.1%} success rate, "
                f"{derived['avg_execution_time']:.1f}s avg time"
            )
        
        return "; ".join(summary_lines)