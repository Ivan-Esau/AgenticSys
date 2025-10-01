"""
Orchestrator module - Clean modular supervisor implementation
Organized into logical submodules for better maintainability.
"""

from .supervisor import Supervisor, run_supervisor

# Export core components
from .core import Router, PerformanceTracker, AgentExecutor

# Export managers
from .managers import IssueManager, PipelineManager, PlanningManager

# Export pipeline components
from .pipeline import PipelineConfig

# Export integrations
from .integrations import MCPIntegration

# Export utilities
from .utils import CompletionMarkers

__all__ = [
    "Supervisor",
    "run_supervisor",
    "Router",
    "PerformanceTracker",
    "AgentExecutor",
    "IssueManager",
    "PipelineManager",
    "PlanningManager",
    "PipelineConfig",
    "MCPIntegration",
    "CompletionMarkers"
]