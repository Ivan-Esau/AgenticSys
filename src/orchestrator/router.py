"""
Task routing for agent orchestration.
Maps tasks to appropriate agents without unnecessary complexity.
"""

from typing import Dict, Any


class Router:
    """Route tasks to appropriate agents."""

    def __init__(self):
        self.valid_tasks = ["planning", "coding", "testing", "review"]
        self.task_stats = {}

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

    def complete_task(self, agent_name: str, success: bool = True):
        """
        Mark a task as completed for tracking.

        Args:
            agent_name: Name of the agent that completed the task
            success: Whether the task was successful
        """
        if agent_name not in self.task_stats:
            self.task_stats[agent_name] = {"success": 0, "failure": 0}

        if success:
            self.task_stats[agent_name]["success"] += 1
        else:
            self.task_stats[agent_name]["failure"] += 1
    
