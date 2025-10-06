"""
MetricsCollector - Core metrics aggregation
Provides clean API for tracking all metrics
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from .models import (
    RunMetrics, IssueMetrics, AgentMetrics, PipelineMetrics,
    TokenUsage, ToolCallMetric, ToolStats, CodeMetrics, DebuggingCycle,
    AgentType, Status, LLMConfig, SystemConfig
)


class MetricsCollector:
    """
    Central metrics collector for tracking all system metrics.
    Thread-safe, handles all metric aggregation automatically.
    """

    def __init__(self, run_id: str, project_id: str, config: SystemConfig):
        """
        Initialize metrics collector.

        Args:
            run_id: Unique run identifier
            project_id: GitLab project ID
            config: System configuration for this run
        """
        self.run_metrics = RunMetrics(
            run_id=run_id,
            project_id=project_id,
            start_time=datetime.now(),
            config=config
        )

        # Active tracking contexts
        self._active_issue: Optional[int] = None
        self._active_agent: Optional[AgentMetrics] = None
        self._active_debugging_cycle: Optional[DebuggingCycle] = None
        self._active_tool_calls: Dict[str, ToolCallMetric] = {}

    # ==================== Run-Level Methods ====================

    def finalize_run(self, status: Status = Status.COMPLETED) -> RunMetrics:
        """
        Finalize the run and calculate all aggregate statistics.

        Args:
            status: Final status of the run

        Returns:
            Complete run metrics
        """
        self.run_metrics.end_time = datetime.now()
        self.run_metrics.duration_seconds = (
            self.run_metrics.end_time - self.run_metrics.start_time
        ).total_seconds()
        self.run_metrics.status = status

        # Aggregate issue statistics
        self.run_metrics.total_issues = len(self.run_metrics.issues)
        self.run_metrics.successful_issues = sum(
            1 for issue in self.run_metrics.issues.values()
            if issue.status == Status.COMPLETED
        )
        self.run_metrics.failed_issues = sum(
            1 for issue in self.run_metrics.issues.values()
            if issue.status == Status.FAILED
        )
        self.run_metrics.skipped_issues = sum(
            1 for issue in self.run_metrics.issues.values()
            if issue.status == Status.SKIPPED
        )

        # Calculate success rate
        if self.run_metrics.total_issues > 0:
            self.run_metrics.success_rate_percent = (
                self.run_metrics.successful_issues / self.run_metrics.total_issues * 100
            )

        # Aggregate costs and tokens
        self.run_metrics.total_tokens = sum(
            issue.total_tokens for issue in self.run_metrics.issues.values()
        )
        self.run_metrics.total_cost_usd = sum(
            issue.total_cost_usd for issue in self.run_metrics.issues.values()
        )

        # Aggregate timing
        self.run_metrics.total_agent_duration_seconds = sum(
            agent.duration_seconds
            for issue in self.run_metrics.issues.values()
            for agent in issue.agent_executions
        )
        self.run_metrics.total_pipeline_duration_seconds = sum(
            pipeline.duration_seconds
            for issue in self.run_metrics.issues.values()
            for pipeline in issue.pipelines
        )

        # Aggregate errors
        self.run_metrics.total_errors = sum(
            len(issue.errors) for issue in self.run_metrics.issues.values()
        )
        self.run_metrics.total_debugging_cycles = sum(
            len(issue.debugging_cycles) for issue in self.run_metrics.issues.values()
        )

        return self.run_metrics

    def get_run_metrics(self) -> RunMetrics:
        """Get current run metrics (without finalizing)"""
        return self.run_metrics

    # ==================== Issue-Level Methods ====================

    def start_issue(self, issue_iid: int) -> IssueMetrics:
        """
        Start tracking a new issue.

        Args:
            issue_iid: GitLab issue IID (project-specific internal ID)

        Returns:
            New issue metrics object
        """
        issue_metrics = IssueMetrics(
            issue_iid=issue_iid,
            run_id=self.run_metrics.run_id,
            start_time=datetime.now(),
            status=Status.IN_PROGRESS
        )

        self.run_metrics.issues[issue_iid] = issue_metrics
        self._active_issue = issue_iid

        return issue_metrics

    def finalize_issue(self, issue_iid: int, status: Status,
                       code_metrics: Optional[CodeMetrics] = None) -> IssueMetrics:
        """
        Finalize an issue and calculate statistics.

        Args:
            issue_iid: Issue IID (project-specific internal ID) to finalize
            status: Final status
            code_metrics: Optional code change metrics

        Returns:
            Finalized issue metrics
        """
        if issue_iid not in self.run_metrics.issues:
            raise ValueError(f"Issue {issue_iid} not found in metrics")

        issue = self.run_metrics.issues[issue_iid]
        issue.end_time = datetime.now()
        issue.duration_seconds = (issue.end_time - issue.start_time).total_seconds()
        issue.status = status

        # Set code metrics
        if code_metrics:
            issue.code_metrics = code_metrics

        # Calculate aggregate agent stats
        issue.total_agent_attempts = len(issue.agent_executions)
        issue.successful_agents = sum(
            1 for agent in issue.agent_executions if agent.success
        )
        issue.failed_agents = sum(
            1 for agent in issue.agent_executions if not agent.success
        )

        # Pipeline stats
        issue.pipeline_success_count = sum(
            1 for p in issue.pipelines if p.status == 'success'
        )
        issue.pipeline_failure_count = sum(
            1 for p in issue.pipelines if p.status == 'failed'
        )

        # Debugging stats
        issue.total_debugging_cycles = len(issue.debugging_cycles)
        issue.resolved_debugging_cycles = sum(
            1 for d in issue.debugging_cycles if d.resolved
        )

        # Aggregate token usage
        issue.total_tokens = sum(
            agent.token_usage.total_tokens for agent in issue.agent_executions
        )
        issue.total_cost_usd = sum(
            agent.token_usage.estimated_cost_usd for agent in issue.agent_executions
        )

        # Calculate first-time-right
        issue.first_time_right = (
            issue.status == Status.COMPLETED and
            issue.total_agent_attempts == 4 and  # One attempt per agent
            issue.pipeline_failure_count == 0 and
            issue.total_debugging_cycles == 0
        )

        # Calculate complexity score (0-100)
        issue.complexity_score = self._calculate_complexity_score(issue)

        self._active_issue = None
        return issue

    def get_issue_metrics(self, issue_iid: int) -> Optional[IssueMetrics]:
        """Get metrics for a specific issue"""
        return self.run_metrics.issues.get(issue_iid)

    # ==================== Agent-Level Methods ====================

    def start_agent(self, agent_type: AgentType, issue_iid: int,
                    attempt_number: int = 1) -> AgentMetrics:
        """
        Start tracking an agent execution.

        Args:
            agent_type: Type of agent
            issue_iid: Issue IID (project-specific internal ID) being worked on
            attempt_number: Attempt number (for retries)

        Returns:
            New agent metrics object
        """
        if issue_iid not in self.run_metrics.issues:
            raise ValueError(f"Issue {issue_iid} not started")

        agent_metrics = AgentMetrics(
            agent_type=agent_type,
            issue_iid=issue_iid,
            attempt_number=attempt_number,
            start_time=datetime.now(),
            status=Status.IN_PROGRESS
        )

        self.run_metrics.issues[issue_iid].agent_executions.append(agent_metrics)
        self._active_agent = agent_metrics

        return agent_metrics

    def finalize_agent(self, success: bool, error_message: Optional[str] = None,
                       token_usage: Optional[TokenUsage] = None) -> AgentMetrics:
        """
        Finalize the current agent execution.

        Args:
            success: Whether agent succeeded
            error_message: Error message if failed
            token_usage: Token usage data

        Returns:
            Finalized agent metrics
        """
        if not self._active_agent:
            raise ValueError("No active agent to finalize")

        self._active_agent.end_time = datetime.now()
        self._active_agent.duration_seconds = (
            self._active_agent.end_time - self._active_agent.start_time
        ).total_seconds()
        self._active_agent.success = success
        self._active_agent.status = Status.COMPLETED if success else Status.FAILED
        self._active_agent.error_message = error_message

        if token_usage:
            self._active_agent.token_usage = token_usage

        # Aggregate tool stats
        self._aggregate_tool_stats(self._active_agent)

        agent = self._active_agent
        self._active_agent = None

        return agent

    # ==================== Token/Cost Tracking ====================

    def record_token_usage(self, input_tokens: int, output_tokens: int,
                           model: str) -> TokenUsage:
        """
        Record token usage and calculate cost.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: LLM model name

        Returns:
            Token usage with calculated cost
        """
        total_tokens = input_tokens + output_tokens
        cost = self._calculate_cost(input_tokens, output_tokens, model)

        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost
        )

    def _calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Calculate cost based on model pricing.

        Pricing per 1M tokens (as of Oct 2025):
        - deepseek-chat: $0.14 input, $0.28 output
        - deepseek-coder: $0.14 input, $0.28 output
        - gpt-4: $30.00 input, $60.00 output
        - gpt-3.5-turbo: $0.50 input, $1.50 output
        - claude-3-opus: $15.00 input, $75.00 output
        - claude-3-sonnet: $3.00 input, $15.00 output
        """
        pricing = {
            'deepseek-chat': {'input': 0.14 / 1_000_000, 'output': 0.28 / 1_000_000},
            'deepseek-coder': {'input': 0.14 / 1_000_000, 'output': 0.28 / 1_000_000},
            'gpt-4': {'input': 30.0 / 1_000_000, 'output': 60.0 / 1_000_000},
            'gpt-4-turbo': {'input': 10.0 / 1_000_000, 'output': 30.0 / 1_000_000},
            'gpt-3.5-turbo': {'input': 0.5 / 1_000_000, 'output': 1.5 / 1_000_000},
            'claude-3-opus': {'input': 15.0 / 1_000_000, 'output': 75.0 / 1_000_000},
            'claude-3-sonnet': {'input': 3.0 / 1_000_000, 'output': 15.0 / 1_000_000},
            'claude-3-haiku': {'input': 0.25 / 1_000_000, 'output': 1.25 / 1_000_000}
        }

        # Default to GPT-4 pricing if model unknown
        model_pricing = pricing.get(model, pricing['gpt-4'])

        cost = (input_tokens * model_pricing['input'] +
                output_tokens * model_pricing['output'])

        return round(cost, 6)  # Round to 6 decimal places

    # ==================== Tool Tracking ====================

    def start_tool_call(self, tool_name: str) -> str:
        """
        Start tracking a tool call.

        Args:
            tool_name: Name of the tool being called

        Returns:
            Unique call ID
        """
        call_id = f"{tool_name}_{int(time.time() * 1000000)}"

        tool_call = ToolCallMetric(
            tool_name=tool_name,
            start_time=datetime.now()
        )

        self._active_tool_calls[call_id] = tool_call

        if self._active_agent:
            self._active_agent.tool_calls.append(tool_call)

        return call_id

    def end_tool_call(self, call_id: str, success: bool = True,
                      error: Optional[str] = None):
        """
        End a tool call.

        Args:
            call_id: Call ID from start_tool_call
            success: Whether call succeeded
            error: Error message if failed
        """
        if call_id not in self._active_tool_calls:
            return

        tool_call = self._active_tool_calls[call_id]
        tool_call.end_time = datetime.now()
        tool_call.duration_ms = (
            tool_call.end_time - tool_call.start_time
        ).total_seconds() * 1000
        tool_call.success = success
        tool_call.error = error

        del self._active_tool_calls[call_id]

    def _aggregate_tool_stats(self, agent: AgentMetrics):
        """Aggregate tool call statistics for an agent"""
        tool_stats: Dict[str, ToolStats] = {}

        for call in agent.tool_calls:
            if call.tool_name not in tool_stats:
                tool_stats[call.tool_name] = ToolStats(tool_name=call.tool_name)

            stats = tool_stats[call.tool_name]
            stats.call_count += 1

            if call.success:
                stats.success_count += 1
            else:
                stats.failure_count += 1
                if call.error:
                    stats.errors.append(call.error)

            stats.total_duration_ms += call.duration_ms

        # Calculate averages
        for stats in tool_stats.values():
            if stats.call_count > 0:
                stats.avg_duration_ms = stats.total_duration_ms / stats.call_count

        agent.tool_stats = tool_stats

    # ==================== Pipeline Tracking ====================

    def record_pipeline(self, pipeline_id: str, commit_sha: str, status: str,
                        triggered_by: str, retry_attempt: int = 0,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        queue_time_seconds: float = 0.0,
                        execution_time_seconds: float = 0.0,
                        failed_jobs: Optional[List[str]] = None,
                        error_type: Optional[str] = None,
                        error_message: Optional[str] = None) -> PipelineMetrics:
        """
        Record a pipeline execution.

        Args:
            pipeline_id: GitLab pipeline ID
            commit_sha: Commit SHA
            status: Pipeline status
            triggered_by: Which agent triggered it
            retry_attempt: Retry attempt number
            start_time: Pipeline start time
            end_time: Pipeline end time
            queue_time_seconds: Time spent in queue
            execution_time_seconds: Execution time
            failed_jobs: List of failed job names
            error_type: Error type if failed
            error_message: Error message if failed

        Returns:
            Pipeline metrics object
        """
        if self._active_issue is None:
            raise ValueError("No active issue for pipeline")

        duration = 0.0
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds()

        pipeline = PipelineMetrics(
            pipeline_id=pipeline_id,
            commit_sha=commit_sha,
            status=status,
            triggered_by=triggered_by,
            retry_attempt=retry_attempt,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            queue_time_seconds=queue_time_seconds,
            execution_time_seconds=execution_time_seconds,
            failed_jobs=failed_jobs or [],
            error_type=error_type,
            error_message=error_message
        )

        self.run_metrics.issues[self._active_issue].pipelines.append(pipeline)

        return pipeline

    # ==================== Debugging Cycle Tracking ====================

    def start_debugging_cycle(self, agent: str, error_type: str,
                              error_message: str) -> DebuggingCycle:
        """
        Start tracking a debugging cycle.

        Args:
            agent: Agent doing the debugging
            error_type: Type of error
            error_message: Error message

        Returns:
            New debugging cycle
        """
        if self._active_issue is None:
            raise ValueError("No active issue for debugging cycle")

        cycle = DebuggingCycle(
            agent=agent,
            error_type=error_type,
            error_message=error_message,
            start_time=datetime.now()
        )

        self.run_metrics.issues[self._active_issue].debugging_cycles.append(cycle)
        self._active_debugging_cycle = cycle

        return cycle

    def record_debug_attempt(self):
        """Record a debugging attempt in the current cycle"""
        if self._active_debugging_cycle:
            self._active_debugging_cycle.attempts += 1

    def end_debugging_cycle(self, resolved: bool,
                            resolution_method: Optional[str] = None):
        """
        End the current debugging cycle.

        Args:
            resolved: Whether the issue was resolved
            resolution_method: How it was resolved
        """
        if not self._active_debugging_cycle:
            return

        self._active_debugging_cycle.end_time = datetime.now()
        self._active_debugging_cycle.duration_seconds = (
            self._active_debugging_cycle.end_time -
            self._active_debugging_cycle.start_time
        ).total_seconds()
        self._active_debugging_cycle.resolved = resolved
        self._active_debugging_cycle.resolution_method = resolution_method

        self._active_debugging_cycle = None

    # ==================== Error Tracking ====================

    def record_error(self, error_type: str, error_message: str,
                     agent: Optional[str] = None, severity: str = "error"):
        """
        Record an error.

        Args:
            error_type: Type of error
            error_message: Error message
            agent: Agent that encountered the error
            severity: Error severity (error, warning, critical)
        """
        if self._active_issue is None:
            return

        error = {
            'type': error_type,
            'message': error_message,
            'agent': agent,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }

        self.run_metrics.issues[self._active_issue].errors.append(error)

    # ==================== Helper Methods ====================

    def _calculate_complexity_score(self, issue: IssueMetrics) -> int:
        """
        Calculate issue complexity score (0-100).

        Based on:
        - Number of agent attempts
        - Number of pipelines
        - Debugging cycles
        - Code changes
        """
        score = 0

        # Agent attempts (0-25 points)
        # More than expected attempts = more complex
        expected_attempts = 4  # One per agent
        extra_attempts = max(0, issue.total_agent_attempts - expected_attempts)
        score += min(25, extra_attempts * 5)

        # Pipeline failures (0-25 points)
        score += min(25, issue.pipeline_failure_count * 10)

        # Debugging cycles (0-25 points)
        score += min(25, issue.total_debugging_cycles * 10)

        # Code changes (0-25 points)
        total_changes = (
            issue.code_metrics.files_created +
            issue.code_metrics.files_modified +
            issue.code_metrics.lines_added +
            issue.code_metrics.lines_deleted
        )
        # Normalize to 0-25 scale (500+ changes = 25 points)
        score += min(25, int(total_changes / 20))

        return min(100, score)
