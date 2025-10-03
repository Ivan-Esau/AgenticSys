"""
Data models for metrics tracking
Clean, typed dataclasses for all metric types
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """Agent types"""
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    REVIEW = "review"


class Status(str, Enum):
    """Execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TokenUsage:
    """LLM token usage and cost"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolCallMetric:
    """Single tool call metric"""
    tool_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tool_name': self.tool_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'success': self.success,
            'error': self.error
        }


@dataclass
class ToolStats:
    """Aggregated tool usage statistics"""
    tool_name: str
    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CodeMetrics:
    """Code change metrics from git"""
    files_created: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    commits: int = 0
    test_coverage_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineMetrics:
    """GitLab pipeline execution metrics"""
    pipeline_id: str
    commit_sha: str
    status: str  # success, failed, canceled, etc.
    triggered_by: str  # Which agent triggered it
    retry_attempt: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    queue_time_seconds: float = 0.0
    execution_time_seconds: float = 0.0
    failed_jobs: List[str] = field(default_factory=list)
    error_type: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pipeline_id': self.pipeline_id,
            'commit_sha': self.commit_sha,
            'status': self.status,
            'triggered_by': self.triggered_by,
            'retry_attempt': self.retry_attempt,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'queue_time_seconds': self.queue_time_seconds,
            'execution_time_seconds': self.execution_time_seconds,
            'failed_jobs': self.failed_jobs,
            'error_type': self.error_type,
            'error_message': self.error_message
        }


@dataclass
class DebuggingCycle:
    """Debugging/retry cycle metrics"""
    agent: str
    error_type: str
    error_message: str
    start_time: datetime
    end_time: Optional[datetime] = None
    attempts: int = 0
    resolved: bool = False
    resolution_method: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent': self.agent,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'attempts': self.attempts,
            'resolved': self.resolved,
            'resolution_method': self.resolution_method,
            'duration_seconds': self.duration_seconds
        }


@dataclass
class AgentMetrics:
    """Metrics for a single agent execution"""
    agent_type: AgentType
    issue_id: int
    attempt_number: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: Status = Status.PENDING
    success: bool = False
    error_message: Optional[str] = None

    # Token usage
    token_usage: TokenUsage = field(default_factory=TokenUsage)

    # Tool usage
    tool_calls: List[ToolCallMetric] = field(default_factory=list)
    tool_stats: Dict[str, ToolStats] = field(default_factory=dict)

    # Retries
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_type': self.agent_type.value,
            'issue_id': self.issue_id,
            'attempt_number': self.attempt_number,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'status': self.status.value,
            'success': self.success,
            'error_message': self.error_message,
            'token_usage': self.token_usage.to_dict(),
            'tool_calls_count': len(self.tool_calls),
            'tool_stats': {k: v.to_dict() for k, v in self.tool_stats.items()},
            'retry_count': self.retry_count
        }


@dataclass
class IssueMetrics:
    """Comprehensive metrics for a single issue"""
    issue_id: int
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: Status = Status.PENDING

    # Agent executions
    agent_executions: List[AgentMetrics] = field(default_factory=list)

    # Aggregate agent stats
    total_agent_attempts: int = 0
    successful_agents: int = 0
    failed_agents: int = 0

    # Pipeline tracking
    pipelines: List[PipelineMetrics] = field(default_factory=list)
    pipeline_success_count: int = 0
    pipeline_failure_count: int = 0

    # Debugging
    debugging_cycles: List[DebuggingCycle] = field(default_factory=list)
    total_debugging_cycles: int = 0
    resolved_debugging_cycles: int = 0

    # Code changes
    code_metrics: CodeMetrics = field(default_factory=CodeMetrics)

    # Aggregate token usage
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Performance indicators
    first_time_right: bool = False  # Succeeded without retries
    complexity_score: int = 0  # Calculated from various factors

    # Errors
    errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'issue_id': self.issue_id,
            'run_id': self.run_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'status': self.status.value,
            'agent_executions': [a.to_dict() for a in self.agent_executions],
            'total_agent_attempts': self.total_agent_attempts,
            'successful_agents': self.successful_agents,
            'failed_agents': self.failed_agents,
            'pipelines': [p.to_dict() for p in self.pipelines],
            'pipeline_success_count': self.pipeline_success_count,
            'pipeline_failure_count': self.pipeline_failure_count,
            'debugging_cycles': [d.to_dict() for d in self.debugging_cycles],
            'total_debugging_cycles': self.total_debugging_cycles,
            'resolved_debugging_cycles': self.resolved_debugging_cycles,
            'code_metrics': self.code_metrics.to_dict(),
            'total_tokens': self.total_tokens,
            'total_cost_usd': self.total_cost_usd,
            'first_time_right': self.first_time_right,
            'complexity_score': self.complexity_score,
            'errors': self.errors
        }


@dataclass
class LLMConfig:
    """LLM configuration for comparative analysis"""
    provider: str
    model: str
    temperature: float
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemConfig:
    """System configuration for comparative analysis"""
    # LLM settings
    llm: LLMConfig

    # Agent settings
    max_retries: int = 3
    retry_delay_seconds: int = 5

    # Testing settings
    min_coverage_percent: float = 70.0

    # Execution settings
    execution_mode: str = "implement_all"  # implement_all, single_issue, analyze
    specific_issue: Optional[int] = None

    # Performance settings
    parallel_execution: bool = False
    timeout_seconds: int = 3600

    def to_dict(self) -> Dict[str, Any]:
        return {
            'llm': self.llm.to_dict(),
            'max_retries': self.max_retries,
            'retry_delay_seconds': self.retry_delay_seconds,
            'min_coverage_percent': self.min_coverage_percent,
            'execution_mode': self.execution_mode,
            'specific_issue': self.specific_issue,
            'parallel_execution': self.parallel_execution,
            'timeout_seconds': self.timeout_seconds
        }


@dataclass
class RunMetrics:
    """Top-level metrics for an entire run"""
    run_id: str
    project_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    status: Status = Status.IN_PROGRESS

    # Configuration (for comparative analysis)
    config: SystemConfig = None

    # Issue metrics
    issues: Dict[int, IssueMetrics] = field(default_factory=dict)

    # Aggregate statistics
    total_issues: int = 0
    successful_issues: int = 0
    failed_issues: int = 0
    skipped_issues: int = 0
    success_rate_percent: float = 0.0

    # Aggregate costs
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    # Aggregate timing
    total_agent_duration_seconds: float = 0.0
    total_pipeline_duration_seconds: float = 0.0

    # Error tracking
    total_errors: int = 0
    total_debugging_cycles: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'run_id': self.run_id,
            'project_id': self.project_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'status': self.status.value,
            'config': self.config.to_dict() if self.config else None,
            'total_issues': self.total_issues,
            'successful_issues': self.successful_issues,
            'failed_issues': self.failed_issues,
            'skipped_issues': self.skipped_issues,
            'success_rate_percent': self.success_rate_percent,
            'total_tokens': self.total_tokens,
            'total_cost_usd': self.total_cost_usd,
            'total_agent_duration_seconds': self.total_agent_duration_seconds,
            'total_pipeline_duration_seconds': self.total_pipeline_duration_seconds,
            'total_errors': self.total_errors,
            'total_debugging_cycles': self.total_debugging_cycles,
            'issues': {k: v.to_dict() for k, v in self.issues.items()}
        }
