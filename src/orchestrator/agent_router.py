"""
Agent routing logic for the supervisor orchestrator.
Handles intelligent agent selection and task routing.
"""

from typing import Dict, Any, Optional, List, Set
from enum import Enum


class AgentType(Enum):
    """Available agent types"""
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    REVIEW = "review"


class TaskType(Enum):
    """Task types that can be routed to agents"""
    ANALYZE_PROJECT = "analyze_project"
    IMPLEMENT_FEATURE = "implement_feature"
    CREATE_TESTS = "create_tests"
    REVIEW_CODE = "review_code"
    FIX_PIPELINE = "fix_pipeline"


class AgentRouter:
    """
    Routes tasks to appropriate agents based on task type and context.
    Implements intelligent agent selection with load balancing and capability matching.
    """
    
    def __init__(self):
        # Agent capabilities mapping
        self.agent_capabilities = {
            AgentType.PLANNING: {
                TaskType.ANALYZE_PROJECT,
            },
            AgentType.CODING: {
                TaskType.IMPLEMENT_FEATURE,
                TaskType.FIX_PIPELINE,
            },
            AgentType.TESTING: {
                TaskType.CREATE_TESTS,
                TaskType.FIX_PIPELINE,
            },
            AgentType.REVIEW: {
                TaskType.REVIEW_CODE,
            }
        }
        
        # Agent load tracking (for future load balancing)
        self.agent_load = {
            AgentType.PLANNING: 0,
            AgentType.CODING: 0,
            AgentType.TESTING: 0,
            AgentType.REVIEW: 0
        }
        
        # Valid task types
        self._valid_task_types = {"planning", "coding", "testing", "review"}
    
    def route_task(self, task_type: str, **kwargs) -> Dict[str, Any]:
        """
        Route a task to the appropriate agent.
        
        Args:
            task_type: Type of task to route
            **kwargs: Task-specific parameters
            
        Returns:
            Dict containing routing decision and parameters
        """
        # Validate task type
        if not self.validate_task_type(task_type):
            return {
                "success": False,
                "error": f"Invalid task type: {task_type}",
                "agent": None
            }
        
        # Route based on task type
        agent_type = self._map_task_to_agent(task_type)
        
        # Validate agent capabilities for this specific request
        if not self._validate_agent_capabilities(agent_type, kwargs):
            return {
                "success": False,
                "error": f"Agent {agent_type.value} cannot handle this request",
                "agent": None
            }
        
        # Prepare routing result
        routing_result = {
            "success": True,
            "agent": agent_type.value,
            "task_type": task_type,
            "parameters": kwargs,
            "routing_metadata": {
                "current_load": self.agent_load.get(agent_type, 0),
                "capabilities_matched": True
            }
        }
        
        # Update load tracking
        self._update_agent_load(agent_type, 1)
        
        return routing_result
    
    def validate_task_type(self, task_type: str) -> bool:
        """
        Validate that task type is supported.
        
        Args:
            task_type: Task type to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if task_type not in self._valid_task_types:
            print(f"[ROUTER] ❌ Unknown task type: {task_type}. Valid types: {self._valid_task_types}")
            return False
        return True
    
    def _map_task_to_agent(self, task_type: str) -> AgentType:
        """
        Map task type to appropriate agent.
        
        Args:
            task_type: Task type to map
            
        Returns:
            AgentType: Appropriate agent for the task
        """
        task_to_agent_map = {
            "planning": AgentType.PLANNING,
            "coding": AgentType.CODING,
            "testing": AgentType.TESTING,
            "review": AgentType.REVIEW
        }
        
        return task_to_agent_map.get(task_type, AgentType.PLANNING)
    
    def _validate_agent_capabilities(self, agent_type: AgentType, task_params: Dict[str, Any]) -> bool:
        """
        Validate that the selected agent can handle the specific task parameters.
        
        Args:
            agent_type: Agent type to validate
            task_params: Task parameters to check
            
        Returns:
            bool: True if agent can handle the task, False otherwise
        """
        # Basic capability validation based on task parameters
        if agent_type == AgentType.CODING:
            # Coding agent needs either issue or fix_mode
            issue = task_params.get("issue")
            fix_mode = task_params.get("fix_mode", False)
            
            if not issue and not fix_mode:
                print(f"[ROUTER] ❌ Coding agent requires either issue or fix_mode")
                return False
        
        elif agent_type == AgentType.REVIEW:
            # Review agent needs both issue and branch
            issue = task_params.get("issue")
            branch = task_params.get("branch")
            
            if not issue or not branch:
                print(f"[ROUTER] ❌ Review agent requires both issue and branch")
                return False
        
        elif agent_type == AgentType.PLANNING:
            # Planning agent just needs basic setup (validated elsewhere)
            pass
        
        elif agent_type == AgentType.TESTING:
            # Testing agent is flexible, can work with or without specific requirements
            pass
        
        return True
    
    def _update_agent_load(self, agent_type: AgentType, load_change: int):
        """
        Update agent load tracking.
        
        Args:
            agent_type: Agent whose load to update
            load_change: Change in load (positive or negative)
        """
        current_load = self.agent_load.get(agent_type, 0)
        self.agent_load[agent_type] = max(0, current_load + load_change)
    
    def complete_task(self, agent_type: str, success: bool = True):
        """
        Mark a task as complete and update load tracking.
        
        Args:
            agent_type: Agent type that completed the task
            success: Whether the task completed successfully
        """
        try:
            agent_enum = AgentType(agent_type)
            self._update_agent_load(agent_enum, -1)
        except ValueError:
            print(f"[ROUTER] ⚠️ Unknown agent type in completion: {agent_type}")
    
    def get_agent_load_status(self) -> Dict[str, Any]:
        """
        Get current agent load status.
        
        Returns:
            Dict containing load information for all agents
        """
        return {
            "agent_loads": {agent.value: load for agent, load in self.agent_load.items()},
            "total_load": sum(self.agent_load.values()),
            "busiest_agent": max(self.agent_load.items(), key=lambda x: x[1])[0].value,
            "available_agents": [
                agent.value for agent, load in self.agent_load.items() 
                if load == 0
            ]
        }
    
    def suggest_optimal_agent(self, task_type: str, priority: str = "normal") -> Optional[str]:
        """
        Suggest optimal agent for a task considering load balancing.
        
        Args:
            task_type: Type of task to route
            priority: Task priority (normal, high, urgent)
            
        Returns:
            Optional[str]: Suggested agent name, or None if none available
        """
        if not self.validate_task_type(task_type):
            return None
        
        agent_type = self._map_task_to_agent(task_type)
        
        # For high priority tasks, always return the capable agent
        if priority in ["high", "urgent"]:
            return agent_type.value
        
        # For normal priority, consider load balancing
        current_load = self.agent_load.get(agent_type, 0)
        
        # If agent is heavily loaded, suggest waiting or alternative
        if current_load > 3:  # Arbitrary threshold
            return None  # Suggest waiting
        
        return agent_type.value
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """
        Get routing statistics and performance metrics.
        
        Returns:
            Dict containing routing statistics
        """
        total_load = sum(self.agent_load.values())
        
        # Calculate load distribution
        load_distribution = {}
        if total_load > 0:
            load_distribution = {
                agent.value: (load / total_load) * 100 
                for agent, load in self.agent_load.items()
            }
        
        # Find bottlenecks
        bottlenecks = [
            agent.value for agent, load in self.agent_load.items() 
            if load > 2  # Threshold for bottleneck
        ]
        
        return {
            "total_active_tasks": total_load,
            "load_distribution": load_distribution,
            "bottlenecks": bottlenecks,
            "routing_efficiency": self._calculate_routing_efficiency(),
            "recommendations": self._generate_routing_recommendations()
        }
    
    def _calculate_routing_efficiency(self) -> float:
        """Calculate routing efficiency score (0.0 to 1.0)."""
        loads = list(self.agent_load.values())
        
        if not loads or sum(loads) == 0:
            return 1.0  # Perfect efficiency when no load
        
        # Calculate load variance (lower variance = better distribution)
        avg_load = sum(loads) / len(loads)
        variance = sum((load - avg_load) ** 2 for load in loads) / len(loads)
        
        # Convert variance to efficiency score (inverse relationship)
        # Lower variance = higher efficiency
        max_variance = avg_load ** 2  # Worst case: all load on one agent
        if max_variance == 0:
            return 1.0
        
        efficiency = 1.0 - (variance / max_variance)
        return max(0.0, min(1.0, efficiency))
    
    def _generate_routing_recommendations(self) -> List[str]:
        """Generate recommendations for routing optimization."""
        recommendations = []
        
        loads = self.agent_load
        total_load = sum(loads.values())
        
        if total_load == 0:
            return ["No active tasks - system idle"]
        
        # Check for overloaded agents
        for agent, load in loads.items():
            if load > 3:
                recommendations.append(f"Agent {agent.value} is overloaded ({load} tasks)")
        
        # Check for underutilized agents
        avg_load = total_load / len(loads)
        for agent, load in loads.items():
            if load == 0 and avg_load > 1:
                recommendations.append(f"Agent {agent.value} is idle while others are busy")
        
        # Load balancing suggestions
        max_load = max(loads.values())
        min_load = min(loads.values())
        if max_load - min_load > 2:
            recommendations.append("Consider load balancing between agents")
        
        if not recommendations:
            recommendations.append("Routing appears well-balanced")
        
        return recommendations
    
    def reset_load_tracking(self):
        """Reset all agent load tracking."""
        self.agent_load = {agent: 0 for agent in self.agent_load}
        print("[ROUTER] Reset agent load tracking")
    
    def get_valid_task_types(self) -> Set[str]:
        """Get set of valid task types."""
        return self._valid_task_types.copy()