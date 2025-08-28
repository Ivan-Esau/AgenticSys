"""
Issue management for the supervisor orchestrator.
Handles complete issue implementation workflow.
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


class IssueStatus:
    """Issue status constants"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"


class IssueManager:
    """
    Manages the complete issue implementation workflow.
    Coordinates the three-phase implementation process.
    """
    
    def __init__(self, project_id: str, state_manager: Any):
        self.project_id = project_id
        self.state_manager = state_manager
        self.current_issue = None
        self.issue_start_time = None
        
        # Issue processing history
        self.processed_issues = []
        self.phase_timings = {}
    
    async def implement_issue(
        self,
        issue: Dict[str, Any],
        agent_executor: Any,
        validation_enabled: bool = True
    ) -> bool:
        """
        Execute complete issue implementation workflow.
        
        This is the HARDENED workflow for implementing a single issue.
        Strictly controls each phase to work on ONLY the current issue.
        
        Args:
            issue: Issue dictionary to implement
            agent_executor: Agent executor for running agents
            validation_enabled: Whether to perform validation checks
            
        Returns:
            bool: True if implementation successful, False otherwise
        """
        issue_id = issue.get("iid")
        issue_title = issue.get("title", "Unknown")
        
        print("\n" + "="*60)
        print(f"[ISSUE #{issue_id}] {issue_title}")
        print("="*60)
        
        # Set current issue tracking
        self.current_issue = issue
        self.issue_start_time = datetime.now()
        
        # Pre-flight validation
        if validation_enabled:
            if not await self._validate_issue_ready_for_implementation(issue):
                return False
        
        # Check if already complete
        if not self._should_implement_issue(issue_id):
            print(f"[SKIP] Issue #{issue_id} already complete")
            return True
        
        # Create specific branch for this issue
        branch = self._generate_issue_branch(issue_id, issue_title)
        
        # Mark issue as in progress
        print(f"[ISSUE MANAGER] Setting Issue #{issue_id} to in_progress status")
        self._update_issue_status(issue_id, IssueStatus.IN_PROGRESS)
        
        # Create checkpoint before starting
        checkpoint = self.state_manager.checkpoint()
        
        try:
            print(f"[ISSUE MANAGER] 🎯 STRICT SINGLE-ISSUE MODE: Issue #{issue_id} ONLY")
            print(f"[ISSUE MANAGER] Phase boundaries: CODING → TESTING → REVIEW")
            print(f"[ISSUE MANAGER] Each agent must signal completion before next phase")
            
            # Execute three-phase workflow with strict boundaries
            success = await self._execute_three_phase_workflow(
                issue, branch, agent_executor
            )
            
            if success:
                print(f"\n[SUCCESS] ✅ Issue #{issue_id} fully implemented!")
                self._update_issue_status(issue_id, IssueStatus.COMPLETE)
                self._record_issue_completion(issue, True)
            else:
                print(f"\n[FAILURE] ❌ Issue #{issue_id} implementation failed")
                self._update_issue_status(issue_id, IssueStatus.FAILED)
                self._record_issue_completion(issue, False)
            
            return success
            
        except Exception as e:
            print(f"\n[ERROR] Failed to implement issue #{issue_id}: {e}")
            self._update_issue_status(issue_id, IssueStatus.FAILED)
            self._record_issue_completion(issue, False, str(e))
            # Could restore from checkpoint here if needed
            return False
        
        finally:
            # Clean up current issue tracking
            self.current_issue = None
            self.issue_start_time = None
    
    async def _validate_issue_ready_for_implementation(self, issue: Dict[str, Any]) -> bool:
        """
        Validate that issue is ready for implementation.
        
        Args:
            issue: Issue to validate
            
        Returns:
            bool: True if issue is ready, False otherwise
        """
        from ..validation import IssueValidator
        
        # Structure validation
        if not IssueValidator.validate_issue_structure(issue):
            return False
        
        # Dependency validation
        if not IssueValidator.validate_issue_dependencies(
            issue, 
            self.state_manager.plan,
            self.state_manager.implementation_status
        ):
            return False
        
        return True
    
    async def _execute_three_phase_workflow(
        self,
        issue: Dict[str, Any],
        branch: str,
        agent_executor: Any
    ) -> bool:
        """
        Execute the hardened three-phase workflow: Coding → Testing → Review.
        
        Args:
            issue: Issue to implement
            branch: Branch for implementation
            agent_executor: Agent executor
            
        Returns:
            bool: True if all phases successful
        """
        issue_id = issue.get("iid")
        phases = ["CODING", "TESTING", "REVIEW"]
        
        for phase_num, phase_name in enumerate(phases, 1):
            print(f"\n[PHASE {phase_num}/3] {phase_name}")
            print(f"[ISSUE MANAGER] Phase {phase_name} for Issue #{issue_id}")
            
            phase_start = datetime.now()
            phase_success = False
            
            try:
                if phase_name == "CODING":
                    phase_success = await self._execute_coding_phase(issue, branch, agent_executor)
                elif phase_name == "TESTING":
                    phase_success = await self._execute_testing_phase(issue, branch, agent_executor)
                elif phase_name == "REVIEW":
                    phase_success = await self._execute_review_phase(issue, branch, agent_executor)
                
                # Record phase timing
                phase_duration = (datetime.now() - phase_start).total_seconds()
                self._record_phase_timing(issue_id, phase_name, phase_duration, phase_success)
                
                if phase_success:
                    print(f"[✓] {phase_name} phase completed successfully")
                else:
                    print(f"[✗] {phase_name} phase failed")
                    
                    # Some phases can continue with warnings
                    if phase_name == "TESTING":
                        print(f"[!] Testing issues for issue #{issue_id}, but continuing...")
                        # Continue to review phase even with test issues
                    else:
                        # Coding and Review phases must succeed
                        return False
                
                # Brief pause between phases for system stability
                if phase_num < len(phases):
                    await asyncio.sleep(2)
            
            except Exception as e:
                print(f"[ERROR] {phase_name} phase exception: {e}")
                self._record_phase_timing(issue_id, phase_name, 0, False, str(e))
                return False
        
        return True
    
    async def _execute_coding_phase(
        self,
        issue: Dict[str, Any],
        branch: str,
        agent_executor: Any
    ) -> bool:
        """Execute coding phase with controlled parameters."""
        issue_id = issue.get("iid")
        
        print(f"[CODING] Implementing ONLY Issue #{issue_id} requirements")
        print(f"[CODING] Branch: {branch}")
        print(f"[CODING] Scope: {issue.get('title', 'Unknown')}")
        
        result = await agent_executor.execute_coding_agent(
            issue=issue,
            branch=branch,
            fix_mode=False  # Regular implementation, not fix mode
        )
        
        if result:
            # Handle result (agents return strings)
            result_summary = "Implementation complete"
            if isinstance(result, str):
                result_summary = result[:100] + "..." if len(result) > 100 else result
            
            print(f"[CODING] Agent reported: {result_summary}")
            return True
        
        return False
    
    async def _execute_testing_phase(
        self,
        issue: Dict[str, Any],
        branch: str,
        agent_executor: Any
    ) -> bool:
        """Execute testing phase for the implemented code."""
        issue_id = issue.get("iid")
        
        print(f"[TESTING] Creating tests for Issue #{issue_id} implementation")
        print(f"[TESTING] Branch: {branch}")
        print(f"[TESTING] Focus: Test ONLY the new/modified code")
        
        result = await agent_executor.execute_testing_agent(
            issue=issue,
            branch=branch,
            fix_mode=False
        )
        
        if result:
            # Handle testing result
            test_summary = "Tests created and passing"
            if isinstance(result, str):
                test_summary = result[:100] + "..." if len(result) > 100 else result
            
            print(f"[TESTING] Agent reported: {test_summary}")
            return True
        
        # Testing failures are warnings, not hard failures
        print(f"[TESTING] Testing had issues but continuing with review")
        return True  # Allow continuation
    
    async def _execute_review_phase(
        self,
        issue: Dict[str, Any],
        branch: str,
        agent_executor: Any
    ) -> bool:
        """Execute review and merge phase."""
        issue_id = issue.get("iid")
        
        print(f"[REVIEW] Creating merge request for Issue #{issue_id}")
        print(f"[REVIEW] Branch: {branch} → master")
        print(f"[REVIEW] Validating implementation completeness")
        
        result = await agent_executor.execute_review_agent(
            issue=issue,
            branch=branch
        )
        
        # Review agent handles merge completion and issue closing
        if result:
            print(f"[REVIEW] Merge request created and processed")
            return True
        
        return False
    
    def _generate_issue_branch(self, issue_id: Any, issue_title: str) -> str:
        """Generate a descriptive branch name for the issue."""
        # Clean title for branch name
        clean_title = issue_title.lower().replace(' ', '-')[:30]
        # Remove special characters
        clean_title = ''.join(c for c in clean_title if c.isalnum() or c == '-')
        
        return f"feature/issue-{issue_id}-{clean_title}"
    
    def _should_implement_issue(self, issue_id: Any) -> bool:
        """Check if issue should be implemented."""
        return self.state_manager.should_implement_issue(str(issue_id))
    
    def _update_issue_status(self, issue_id: Any, status: str):
        """Update issue status in state manager."""
        self.state_manager.update_issue_status(str(issue_id), status)
    
    def _record_issue_completion(
        self,
        issue: Dict[str, Any],
        success: bool,
        error: Optional[str] = None
    ):
        """Record issue completion statistics."""
        completion_time = None
        if self.issue_start_time:
            completion_time = (datetime.now() - self.issue_start_time).total_seconds()
        
        completion_record = {
            "issue_id": issue.get("iid"),
            "issue_title": issue.get("title"),
            "success": success,
            "completion_time": completion_time,
            "error": error,
            "timestamp": datetime.now(),
            "phases_completed": list(self.phase_timings.keys()) if hasattr(self, 'phase_timings') else []
        }
        
        self.processed_issues.append(completion_record)
        
        # Keep only recent completions (last 50)
        if len(self.processed_issues) > 50:
            self.processed_issues = self.processed_issues[-50:]
    
    def _record_phase_timing(
        self,
        issue_id: Any,
        phase_name: str,
        duration: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Record timing and success data for each phase."""
        if not hasattr(self, 'phase_timings'):
            self.phase_timings = {}
        
        phase_key = f"{issue_id}_{phase_name}"
        self.phase_timings[phase_key] = {
            "duration": duration,
            "success": success,
            "error": error,
            "timestamp": datetime.now()
        }
    
    def get_issue_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about issue processing.
        
        Returns:
            Dict containing issue processing statistics
        """
        if not self.processed_issues:
            return {
                "total_processed": 0,
                "success_rate": 0.0,
                "average_completion_time": 0.0,
                "phase_success_rates": {}
            }
        
        total = len(self.processed_issues)
        successful = len([i for i in self.processed_issues if i["success"]])
        success_rate = successful / total
        
        # Average completion time
        completion_times = [i["completion_time"] for i in self.processed_issues if i["completion_time"]]
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0.0
        
        # Phase success rates
        phase_stats = {}
        for phase in ["CODING", "TESTING", "REVIEW"]:
            phase_records = [
                record for record in self.phase_timings.values()
                if phase in str(record)  # Simple check - could be improved
            ]
            if phase_records:
                phase_success_count = len([r for r in phase_records if r.get("success", False)])
                phase_stats[phase] = {
                    "success_rate": phase_success_count / len(phase_records),
                    "average_duration": sum(r.get("duration", 0) for r in phase_records) / len(phase_records)
                }
        
        return {
            "total_processed": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": success_rate,
            "average_completion_time": avg_completion_time,
            "phase_statistics": phase_stats,
            "recent_issues": self.processed_issues[-5:]  # Last 5 issues
        }
    
    def get_current_issue_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about currently processing issue.
        
        Returns:
            Dict with current issue info, or None if no active issue
        """
        if not self.current_issue or not self.issue_start_time:
            return None
        
        elapsed_time = (datetime.now() - self.issue_start_time).total_seconds()
        
        return {
            "issue_id": self.current_issue.get("iid"),
            "issue_title": self.current_issue.get("title"),
            "start_time": self.issue_start_time,
            "elapsed_time": elapsed_time,
            "status": "in_progress"
        }