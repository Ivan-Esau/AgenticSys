"""
Unified State Management for GitLab Agent System
Based on LangGraph memory patterns
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path


class ProjectState:
    """
    Shared state for all agents in a project.
    Implements the LangGraph memory pattern with checkpointing support.
    
    This is the "brain" of the AI system - stores all knowledge about the project
    to avoid redundant operations and enable intelligent decision-making.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.thread_id = f"thread_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Core project information
        self.project_info: Optional[Dict] = None
        self.default_branch: str = "master"
        self.current_branch: Optional[str] = None
        self.current_issue: Optional[str] = None
        
        # Technology stack preferences for new projects
        self.tech_stack: Optional[Dict[str, str]] = None
        
        # File knowledge cache - the most important optimization
        # Avoids redundant API calls across agents
        # Simple overwrite strategy: new content always overwrites old
        self.file_cache: Dict[str, Dict[str, Any]] = {}
        
        # Implementation tracking
        self.issues: List[Dict] = []
        self.implementation_order: List[str] = []
        self.implementation_status: Dict[str, str] = {}  # issue_id -> status
        self.completed_issues: List[str] = []
        
        # Plan from planning agent
        self.plan: Optional[Dict] = None
        
        # Handoff context between agents
        self.handoff_context: Dict[str, Any] = {}
        
        # Checkpoint history for recovery
        self.checkpoints: List[Dict] = []
    
    def get_file_implementation_status(self, file_path: str) -> str:
        """Get implementation status of a specific file"""
        if file_path not in self.file_cache:
            return "unknown"
        
        cache_entry = self.file_cache[file_path]
        return cache_entry.get("implementation_status", "unknown")
    
    def update_file_implementation_status(self, file_path: str, status: str) -> None:
        """Update implementation status of a file"""
        if file_path in self.file_cache:
            self.file_cache[file_path]["implementation_status"] = status
            self.file_cache[file_path]["updated_at"] = datetime.now().isoformat()
    
    def get_current_issue(self) -> Optional[Dict]:
        """Get current issue details"""
        if not self.current_issue:
            return None
        return next((issue for issue in self.issues if issue.get('iid') == self.current_issue), None)
        
    def cache_file(self, path: str, content: str, branch: Optional[str] = None) -> None:
        """Cache file content - always overwrites existing cache"""
        target_branch = branch or self.current_branch or self.default_branch
        
        self.file_cache[path] = {
            "content": content,
            "branch": target_branch,
            "cached_at": datetime.now().isoformat(),
            "status": self._analyze_file_status(content)
        }
    
    def get_cached_file(self, path: str) -> Optional[str]:
        """Get cached file if available - no expiration, cache is always valid until overwritten"""
        if path not in self.file_cache:
            return None
            
        return self.file_cache[path]["content"]
    
    def _analyze_file_status(self, content: str) -> str:
        """Determine if file is empty, partial, or complete"""
        if not content or len(content.strip()) == 0:
            return "empty"
        
        # Check for actual implementation
        lines = content.strip().split('\n')
        code_lines = [
            line for line in lines 
            if line.strip() and not line.strip().startswith(('//', '#', '*'))
        ]
        
        if len(code_lines) < 5:  # Less than 5 lines of actual code
            return "empty"
        
        content_lower = content.lower()
        if 'todo' in content_lower or 'implement' in content_lower:
            return "partial"
            
        # Check for actual implementation markers
        if any(marker in content for marker in ['class ', 'function ', 'def ', 'export ']):
            return "complete"
        
        return "empty"
    
    def set_handoff(self, from_agent: str, to_agent: str, context: Dict) -> None:
        """Set handoff context for agent coordination"""
        self.handoff_context = {
            "from": from_agent,
            "to": to_agent,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_handoff(self, agent_name: str) -> Optional[Dict]:
        """Get handoff context if this agent is the recipient"""
        if self.handoff_context.get("to") == agent_name:
            return self.handoff_context.get("")
        return None
    
    def update_issue_status(self, issue_id: str, status: str) -> None:
        """Update implementation status of an issue"""
        self.implementation_status[issue_id] = status
        if status == "complete" and issue_id not in self.completed_issues:
            self.completed_issues.append(issue_id)
    
    def should_implement_issue(self, issue_id: str) -> bool:
        """Check if an issue needs implementation"""
        status = self.implementation_status.get(issue_id, "pending")
        return status in ["pending", "in_progress", "failed"]
    
    def checkpoint(self) -> Dict:
        """Create a checkpoint of current state"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "thread_id": self.thread_id,
            "project_id": self.project_id,
            "current_branch": self.current_branch,
            "current_issue": self.current_issue,
            "completed_issues": self.completed_issues.copy(),
            "implementation_status": self.implementation_status.copy(),
            "file_cache_keys": list(self.file_cache.keys()),
            "handoff_context": self.handoff_context.copy()
        }
        self.checkpoints.append(checkpoint)
        return checkpoint
    
    def restore_from_checkpoint(self, checkpoint: Dict) -> None:
        """Restore state from a checkpoint"""
        self.thread_id = checkpoint.get("thread_id", self.thread_id)
        self.current_branch = checkpoint.get("current_branch")
        self.current_issue = checkpoint.get("current_issue")
        self.completed_issues = checkpoint.get("completed_issues", [])
        self.implementation_status = checkpoint.get("implementation_status", {})
        self.handoff_context = checkpoint.get("handoff_context", {})
    
    def get_summary(self) -> Dict:
        """Get summary of current state"""
        return {
            "project_id": self.project_id,
            "thread_id": self.thread_id,
            "current_branch": self.current_branch,
            "current_issue": self.current_issue,
            "total_issues": len(self.issues),
            "completed_issues": len(self.completed_issues),
            "cached_files": len(self.file_cache),
            "checkpoints": len(self.checkpoints),
            "file_status": self._get_file_status_summary()
        }
    
    def _get_file_status_summary(self) -> Dict[str, int]:
        """Get summary of file statuses"""
        summary = {"empty": 0, "partial": 0, "complete": 0}
        for entry in self.file_cache.values():
            status = entry.get("status", "empty")
            if status in summary:
                summary[status] += 1
        return summary
    
    def save_to_file(self, filepath: Optional[Path] = None) -> Path:
        """Save state to JSON file for persistence"""
        if filepath is None:
            filepath = Path(f"state_{self.project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        state_dict = {
            "project_id": self.project_id,
            "thread_id": self.thread_id,
            "summary": self.get_summary(),
            "latest_checkpoint": self.checkpoints[-1] if self.checkpoints else None,
            "plan": self.plan,
            "implementation_status": self.implementation_status,
            "completed_issues": self.completed_issues
        }
        
        with open(filepath, 'w') as f:
            json.dump(state_dict, f, indent=2)
        
        return filepath
    
    @classmethod
    def load_from_file(cls, filepath: Path) -> "ProjectState":
        """Load state from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        state = cls(data["project_id"])
        state.thread_id = data.get("thread_id", state.thread_id)
        state.plan = data.get("plan")
        state.implementation_status = data.get("implementation_status", {})
        state.completed_issues = data.get("completed_issues", [])
        
        # Restore from latest checkpoint if available
        if data.get("latest_checkpoint"):
            state.restore_from_checkpoint(data["latest_checkpoint"])
        
        return state


class StateManager:
    """
    Global state manager for all projects.
    Implements the checkpointer pattern from LangGraph.
    """
    
    _instance = None
    _states: Dict[str, ProjectState] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
        return cls._instance
    
    def get_or_create_state(self, project_id: str) -> ProjectState:
        """Get existing state or create new one"""
        if project_id not in self._states:
            self._states[project_id] = ProjectState(project_id)
        return self._states[project_id]
    
    def clear_state(self, project_id: str) -> None:
        """Clear state for a project"""
        if project_id in self._states:
            del self._states[project_id]
    
    def checkpoint_all(self) -> Dict[str, Dict]:
        """Create checkpoints for all active states"""
        checkpoints = {}
        for project_id, state in self._states.items():
            checkpoints[project_id] = state.checkpoint()
        return checkpoints


# Global state manager instance
state_manager = StateManager()


def get_project_state(project_id: str) -> ProjectState:
    """Get or create project state - main entry point for agents"""
    return state_manager.get_or_create_state(project_id)