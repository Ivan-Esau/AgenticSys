"""
MetricsContext - Context managers for automatic tracking
Makes it easy to track metrics with minimal code
"""

from typing import Optional
from contextlib import contextmanager
from .collector import MetricsCollector
from .models import AgentType, TokenUsage


class MetricsContext:
    """
    Context manager wrapper for MetricsCollector.
    Provides clean API with automatic cleanup.
    """

    def __init__(self, collector: MetricsCollector):
        """
        Initialize context.

        Args:
            collector: Metrics collector to wrap
        """
        self.collector = collector

    @contextmanager
    def track_issue(self, issue_iid: int):
        """
        Context manager for tracking an issue.

        Usage:
            with metrics.track_issue(issue_iid=3):
                # Work on issue
                pass

        Args:
            issue_iid: Issue IID (project-specific internal ID) to track

        Yields:
            Issue metrics object
        """
        issue_metrics = self.collector.start_issue(issue_iid)

        try:
            yield issue_metrics
        finally:
            # Issue will be finalized explicitly by caller
            pass

    @contextmanager
    def track_agent(self, agent_type: AgentType, issue_iid: int,
                    attempt_number: int = 1):
        """
        Context manager for tracking an agent execution.

        Usage:
            with metrics.track_agent(AgentType.CODING, issue_iid=3) as agent:
                # Agent work
                agent.success = True

        Args:
            agent_type: Type of agent
            issue_iid: Issue IID (project-specific internal ID) being worked on
            attempt_number: Attempt number

        Yields:
            Agent metrics object
        """
        agent_metrics = self.collector.start_agent(
            agent_type, issue_iid, attempt_number
        )

        success = False
        error_message = None
        token_usage = None

        try:
            yield agent_metrics
            success = True
        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            self.collector.finalize_agent(
                success=success,
                error_message=error_message,
                token_usage=token_usage
            )

    @contextmanager
    def track_tool_call(self, tool_name: str):
        """
        Context manager for tracking a tool call.

        Usage:
            with metrics.track_tool_call("create_branch"):
                # Call tool
                pass

        Args:
            tool_name: Name of tool being called

        Yields:
            Call ID
        """
        call_id = self.collector.start_tool_call(tool_name)

        success = True
        error = None

        try:
            yield call_id
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            self.collector.end_tool_call(call_id, success=success, error=error)

    @contextmanager
    def track_debugging_cycle(self, agent: str, error_type: str,
                              error_message: str):
        """
        Context manager for tracking a debugging cycle.

        Usage:
            with metrics.track_debugging_cycle("coding", "test_failure", msg) as cycle:
                # Debugging attempts
                cycle.attempts += 1
                # ...
                cycle.resolved = True

        Args:
            agent: Agent doing the debugging
            error_type: Type of error
            error_message: Error message

        Yields:
            Debugging cycle object
        """
        cycle = self.collector.start_debugging_cycle(
            agent, error_type, error_message
        )

        resolved = False
        resolution_method = None

        try:
            yield cycle
            resolved = cycle.resolved
        except Exception:
            resolved = False
            raise
        finally:
            self.collector.end_debugging_cycle(
                resolved=resolved,
                resolution_method=resolution_method
            )


# Decorator for automatic agent tracking
def track_agent_execution(agent_type: AgentType, collector: MetricsCollector):
    """
    Decorator for automatic agent execution tracking.

    Usage:
        @track_agent_execution(AgentType.CODING, metrics_collector)
        async def execute_coding_agent(issue_iid: int):
            # Agent logic
            return True

    Args:
        agent_type: Type of agent
        collector: Metrics collector

    Returns:
        Decorated function
    """
    def decorator(func):
        async def wrapper(issue_iid: int, *args, **kwargs):
            context = MetricsContext(collector)

            with context.track_agent(agent_type, issue_iid):
                result = await func(issue_iid, *args, **kwargs)
                return result

        return wrapper
    return decorator
