"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class ExecutionMode(str, Enum):
    """Execution modes for the system"""
    IMPLEMENT_ALL = "implement_all"
    SINGLE_ISSUE = "single_issue"
    ANALYSIS_ONLY = "analysis"


class SystemConfig(BaseModel):
    """System configuration request"""
    project_id: str = Field(..., description="GitLab project ID")
    mode: ExecutionMode = Field(default=ExecutionMode.IMPLEMENT_ALL)
    specific_issue: Optional[int] = Field(default=None, description="Specific issue number for single issue mode")
    # tech_stack removed - now auto-detected from project files
    auto_merge: bool = Field(default=False, description="Automatically merge successful MRs")
    debug: bool = Field(default=False, description="Enable debug output")
    min_coverage: float = Field(default=70.0, description="Minimum test coverage percentage")


class SystemStatus(BaseModel):
    """System status response"""
    running: bool
    current_stage: Optional[str]
    current_agent: Optional[str]
    current_issue: Optional[Dict[str, Any]]
    progress: float
    start_time: Optional[datetime]
    stats: Dict[str, Any]


class AgentOutput(BaseModel):
    """Agent output event"""
    agent: str
    timestamp: datetime
    content: str
    level: str = "info"  # info, warning, error, success


class ToolUse(BaseModel):
    """Tool usage event"""
    agent: str
    tool: str
    timestamp: datetime
    input: Dict[str, Any]
    output: Optional[Any]
    duration_ms: Optional[int]
    success: bool


class PipelineStage(BaseModel):
    """Pipeline stage information"""
    name: str
    status: str  # pending, running, completed, failed
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    result: Optional[Dict[str, Any]]


class IssueStatus(BaseModel):
    """Issue processing status"""
    issue_id: int
    title: str
    status: str  # pending, processing, completed, failed
    stages: List[PipelineStage]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    error: Optional[str]


class ProjectInfo(BaseModel):
    """GitLab project information"""
    id: str
    name: str
    description: Optional[str]
    default_branch: str
    web_url: str
    issues_count: int
    open_issues: int


class APIResponse(BaseModel):
    """Standard API response"""
    success: bool
    message: Optional[str]
    data: Optional[Any]


class WebSocketMessage(BaseModel):
    """WebSocket message structure"""
    type: str
    data: Any
    timestamp: datetime = Field(default_factory=datetime.now)