"""
Task routing for agent orchestration.
Maps tasks to appropriate agents without unnecessary complexity.
"""

from typing import Dict, Any


class Router:
    """Route tasks to appropriate agents."""
    
    def __init__(self):
        self.valid_tasks = ["planning", "coding", "testing", "review"]
    
    def route_task(self, task_type: str, **kwargs) -> Dict[str, Any]:
        """
        Route a task to the appropriate agent.
        
        Args:
            task_type: Type of task to route
            **kwargs: Task parameters
            
        Returns:
            Dict with routing decision
        """
        if task_type not in self.valid_tasks:
            return {
                "success": False,
                "error": f"Invalid task type: {task_type}. Valid types: {self.valid_tasks}",
                "agent": None
            }
        
        return {
            "success": True,
            "agent": task_type,
            "task_type": task_type,
            "parameters": kwargs
        }
    
    def complete_task(self, agent_type: str, success: bool = True):
        """Mark task as complete (compatibility method)."""
        pass  # No load tracking needed in streamlined version