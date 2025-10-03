"""
Metrics Data Classes
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class AgentMetrics:
    """Metrics for a single agent execution"""
    agent_name: str
    issue_id: int
    attempt_number: int
    start_time: datetime
    end_time: Optional[datetime] = None
    success: bool = False
    error_message: Optional[str] = None
    retries: int = 0

    def duration(self) -> float:
        """Calculate execution duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'agent_name': self.agent_name,
            'issue_id': self.issue_id,
            'attempt_number': self.attempt_number,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration(),
            'success': self.success,
            'error_message': self.error_message,
            'retries': self.retries
        }


@dataclass
class PipelineMetrics:
    """Metrics for a single pipeline execution"""
    pipeline_id: str
    issue_id: int
    commit_sha: str
    triggered_by: str  # 'coding', 'testing', 'review'
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = 'pending'  # 'pending', 'running', 'success', 'failed'
    failed_jobs: List[str] = field(default_factory=list)
    error_type: Optional[str] = None  # 'test_failure', 'build_error', 'lint_error', etc.
    retry_attempt: int = 0  # Which retry is this (0 = first attempt)

    def duration(self) -> float:
        """Calculate pipeline duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'pipeline_id': self.pipeline_id,
            'issue_id': self.issue_id,
            'commit_sha': self.commit_sha,
            'triggered_by': self.triggered_by,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration(),
            'status': self.status,
            'failed_jobs': self.failed_jobs,
            'error_type': self.error_type,
            'retry_attempt': self.retry_attempt
        }


@dataclass
class DebuggingCycle:
    """Represents a complete debugging cycle"""
    issue_id: int
    agent: str
    error_type: str
    error_message: str
    start_time: datetime
    end_time: Optional[datetime] = None
    attempts: int = 0
    resolved: bool = False
    resolution_method: Optional[str] = None  # How it was resolved

    def duration(self) -> float:
        """Calculate cycle duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'issue_id': self.issue_id,
            'agent': self.agent,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration(),
            'attempts': self.attempts,
            'resolved': self.resolved,
            'resolution_method': self.resolution_method
        }
