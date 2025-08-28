"""
Summary reporting for the supervisor orchestrator.
Generates execution summaries and reports.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class SummaryReporter:
    """
    Generates summaries and reports for supervisor execution.
    Observer pattern - collects and formats information for reporting.
    """
    
    def __init__(self, project_id: str, thread_id: str):
        self.project_id = project_id
        self.thread_id = thread_id
        self.start_time = datetime.now()
        self.end_time = None
        
        # Summary data collection
        self.execution_mode = None
        self.issues_processed = []
        self.files_modified = 0
        self.checkpoints_created = 0
        self.errors_encountered = []
        self.warnings_issued = []
    
    def set_execution_mode(self, mode: str):
        """Set the execution mode for the summary."""
        self.execution_mode = mode
    
    def record_issue_processed(self, issue: Dict[str, Any], status: str):
        """
        Record that an issue was processed.
        
        Args:
            issue: Issue that was processed
            status: Final status (complete, failed, etc.)
        """
        self.issues_processed.append({
            "iid": issue.get("iid"),
            "title": issue.get("title", "Unknown"),
            "status": status,
            "timestamp": datetime.now()
        })
    
    def record_error(self, error: str, component: str = "unknown"):
        """
        Record an error that occurred during execution.
        
        Args:
            error: Error message
            component: Component where error occurred
        """
        self.errors_encountered.append({
            "error": error,
            "component": component,
            "timestamp": datetime.now()
        })
    
    def record_warning(self, warning: str, component: str = "unknown"):
        """
        Record a warning issued during execution.
        
        Args:
            warning: Warning message
            component: Component that issued warning
        """
        self.warnings_issued.append({
            "warning": warning,
            "component": component,
            "timestamp": datetime.now()
        })
    
    def set_files_modified(self, count: int):
        """Set the number of files modified during execution."""
        self.files_modified = count
    
    def increment_checkpoints(self):
        """Increment the checkpoint counter."""
        self.checkpoints_created += 1
    
    def finalize_execution(self):
        """Mark execution as complete."""
        self.end_time = datetime.now()
    
    def generate_summary(
        self,
        state_info: Optional[Dict[str, Any]] = None,
        agent_metrics: Optional[Dict[str, Any]] = None,
        performance_alerts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive execution summary.
        
        Args:
            state_info: Project state information
            agent_metrics: Agent performance metrics
            performance_alerts: Performance alerts
            
        Returns:
            Dict containing complete summary
        """
        duration = None
        if self.end_time and self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()
        
        summary = {
            "execution_info": {
                "project_id": self.project_id,
                "thread_id": self.thread_id,
                "mode": self.execution_mode,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": duration
            },
            
            "issue_summary": self._generate_issue_summary(),
            
            "performance_summary": {
                "files_modified": self.files_modified,
                "checkpoints_created": self.checkpoints_created,
                "errors_count": len(self.errors_encountered),
                "warnings_count": len(self.warnings_issued)
            },
            
            "quality_metrics": self._generate_quality_metrics()
        }
        
        # Add state information if provided
        if state_info:
            summary["state_info"] = state_info
        
        # Add agent metrics if provided
        if agent_metrics:
            summary["agent_metrics"] = agent_metrics
        
        # Add performance alerts if provided
        if performance_alerts:
            summary["performance_alerts"] = performance_alerts
        
        return summary
    
    def _generate_issue_summary(self) -> Dict[str, Any]:
        """Generate summary of issue processing."""
        total_issues = len(self.issues_processed)
        completed_issues = len([i for i in self.issues_processed if i["status"] == "complete"])
        failed_issues = len([i for i in self.issues_processed if i["status"] == "failed"])
        
        return {
            "total_processed": total_issues,
            "completed": completed_issues,
            "failed": failed_issues,
            "success_rate": (completed_issues / total_issues) if total_issues > 0 else 0.0,
            "issues": self.issues_processed
        }
    
    def _generate_quality_metrics(self) -> Dict[str, Any]:
        """Generate quality metrics for the execution."""
        total_issues = len(self.issues_processed)
        errors = len(self.errors_encountered)
        warnings = len(self.warnings_issued)
        
        # Calculate quality score (0.0 to 1.0)
        quality_score = 1.0
        
        if total_issues > 0:
            # Reduce score for failed issues
            failed_issues = len([i for i in self.issues_processed if i["status"] == "failed"])
            quality_score -= (failed_issues / total_issues) * 0.5
        
        # Reduce score for errors
        if errors > 0:
            quality_score -= min(0.3, errors * 0.1)
        
        # Reduce score for warnings (less severe)
        if warnings > 0:
            quality_score -= min(0.2, warnings * 0.05)
        
        quality_score = max(0.0, quality_score)  # Don't go below 0
        
        return {
            "quality_score": quality_score,
            "error_density": errors / max(1, total_issues),
            "warning_density": warnings / max(1, total_issues),
            "reliability": "high" if quality_score > 0.8 else "medium" if quality_score > 0.6 else "low"
        }
    
    def print_console_summary(
        self,
        state_info: Optional[Dict[str, Any]] = None,
        agent_metrics: Optional[Dict[str, Any]] = None,
        include_details: bool = False
    ):
        """
        Print a formatted summary to console.
        
        Args:
            state_info: Project state information
            agent_metrics: Agent performance metrics  
            include_details: Whether to include detailed information
        """
        print("\n" + "="*60)
        print("EXECUTION SUMMARY")
        print("="*60)
        
        # Basic info
        print(f"Project: {self.project_id}")
        print(f"Thread: {self.thread_id}")
        if self.execution_mode:
            print(f"Mode: {self.execution_mode}")
        
        # Duration
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            print(f"Duration: {duration}")
        
        # Issue summary
        issue_summary = self._generate_issue_summary()
        print(f"Issues: {issue_summary['completed']}/{issue_summary['total_processed']} complete")
        
        if issue_summary['total_processed'] > 0:
            print(f"Success Rate: {issue_summary['success_rate']:.1%}")
        
        # State info if provided
        if state_info:
            print(f"Cached Files: {state_info.get('cached_files', 'N/A')}")
            print(f"Checkpoints: {state_info.get('checkpoints', 'N/A')}")
            
            file_status = state_info.get('file_status', {})
            if file_status:
                print(f"File Status: Empty={file_status.get('empty', 0)}, "
                      f"Partial={file_status.get('partial', 0)}, "
                      f"Complete={file_status.get('complete', 0)}")
        
        # Agent metrics if provided
        if agent_metrics:
            print("\nAgent Metrics:")
            for agent, metrics in agent_metrics.items():
                if metrics.get("calls", 0) > 0:
                    error_rate = (metrics.get("errors", 0) / metrics["calls"]) * 100
                    print(f"  {agent}: {metrics['calls']} calls, "
                          f"{metrics.get('errors', 0)} errors ({error_rate:.1f}%)")
        
        # Performance summary
        if self.files_modified > 0:
            print(f"Files Modified: {self.files_modified}")
        
        if self.checkpoints_created > 0:
            print(f"Checkpoints Created: {self.checkpoints_created}")
        
        # Errors and warnings
        if self.errors_encountered:
            print(f"Errors: {len(self.errors_encountered)}")
            if include_details:
                for error in self.errors_encountered[-3:]:  # Show last 3 errors
                    print(f"  - {error['component']}: {error['error']}")
        
        if self.warnings_issued:
            print(f"Warnings: {len(self.warnings_issued)}")
            if include_details:
                for warning in self.warnings_issued[-3:]:  # Show last 3 warnings
                    print(f"  - {warning['component']}: {warning['warning']}")
        
        # Quality score
        quality_metrics = self._generate_quality_metrics()
        print(f"Quality Score: {quality_metrics['quality_score']:.2f} ({quality_metrics['reliability']})")
        
        print("\n[COMPLETE] Orchestration finished")
    
    def export_summary_json(self, file_path: str, **kwargs) -> bool:
        """
        Export summary to JSON file.
        
        Args:
            file_path: Path to save JSON file
            **kwargs: Additional data to include in summary
            
        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            import json
            from pathlib import Path
            
            summary = self.generate_summary(**kwargs)
            
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON file
            with open(file_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)  # default=str handles datetime
            
            print(f"[EXPORT] Summary exported to {file_path}")
            return True
            
        except Exception as e:
            print(f"[EXPORT] Failed to export summary: {e}")
            return False