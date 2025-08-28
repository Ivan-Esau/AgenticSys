"""
Pipeline management for the supervisor orchestrator.
Handles pipeline failures and retry logic.
"""

import asyncio
from typing import Dict, Any, Optional, List
from enum import Enum


class PipelineFailureType(Enum):
    """Types of pipeline failures"""
    TESTS = "PIPELINE_FAILED_TESTS"
    BUILD = "PIPELINE_FAILED_BUILD" 
    LINT = "PIPELINE_FAILED_LINT"
    DEPLOY = "PIPELINE_FAILED_DEPLOY"
    UNKNOWN = "PIPELINE_FAILED_UNKNOWN"


class PipelineManager:
    """
    Manages pipeline failures and retry logic.
    Handles self-healing pipeline operations.
    """
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.retry_counts = {}  # Track retry counts per branch/failure type
        self.failure_history = []  # Track failure patterns for learning
    
    async def handle_pipeline_failure(
        self,
        failure_result: str,
        branch: str,
        agent_executor: Any  # Reference to agent executor for recovery
    ) -> bool:
        """
        Handle pipeline failures with intelligent routing to recovery agents.
        
        Args:
            failure_result: Failure result string from review agent
            branch: Branch where failure occurred
            agent_executor: Agent executor for running recovery agents
            
        Returns:
            bool: True if recovery was successful, False otherwise
        """
        # Parse failure type and details
        failure_type, error_details = self._parse_failure_result(failure_result)
        
        # Check retry limits
        retry_key = f"{branch}_{failure_type.value}"
        retry_count = self.retry_counts.get(retry_key, 0)
        
        if retry_count >= self.max_retries:
            print(f"\n[PIPELINE] ❌ Maximum retries reached for {failure_type.value} on {branch}")
            self._record_failure(failure_type, branch, error_details, "max_retries_exceeded")
            return False
        
        # Increment retry count
        self.retry_counts[retry_key] = retry_count + 1
        print(f"\n[PIPELINE] 🔄 Handling {failure_type.value} (attempt {retry_count + 1}/{self.max_retries})")
        print(f"[PIPELINE] Branch: {branch}")
        print(f"[PIPELINE] Error: {error_details}")
        
        # Route to appropriate recovery strategy
        recovery_success = await self._route_failure_to_recovery(
            failure_type, error_details, branch, agent_executor
        )
        
        # Record the outcome
        outcome = "recovered" if recovery_success else "recovery_failed"
        self._record_failure(failure_type, branch, error_details, outcome)
        
        return recovery_success
    
    def _parse_failure_result(self, failure_result: str) -> tuple[PipelineFailureType, str]:
        """
        Parse failure result string to extract type and details.
        
        Args:
            failure_result: Raw failure result from agent
            
        Returns:
            Tuple of (failure_type, error_details)
        """
        if not isinstance(failure_result, str):
            return PipelineFailureType.UNKNOWN, str(failure_result)
        
        # Try to extract failure type and details
        if ": " in failure_result:
            failure_part, error_details = failure_result.split(": ", 1)
        else:
            failure_part = failure_result
            error_details = ""
        
        # Map to failure type enum
        failure_type = PipelineFailureType.UNKNOWN
        for ft in PipelineFailureType:
            if ft.value in failure_part:
                failure_type = ft
                break
        
        return failure_type, error_details
    
    async def _route_failure_to_recovery(
        self,
        failure_type: PipelineFailureType,
        error_details: str,
        branch: str,
        agent_executor: Any
    ) -> bool:
        """
        Route pipeline failure to appropriate recovery agent.
        
        Args:
            failure_type: Type of pipeline failure
            error_details: Detailed error information
            branch: Branch where failure occurred
            agent_executor: Agent executor for running recovery
            
        Returns:
            bool: True if recovery successful, False otherwise
        """
        try:
            if failure_type == PipelineFailureType.TESTS:
                print("[PIPELINE] → Routing to Testing Agent for test fixes")
                return await agent_executor.execute_testing_agent(
                    issue=None,
                    branch=branch,
                    fix_mode=True,
                    error_context=error_details
                )
            
            elif failure_type in [
                PipelineFailureType.BUILD, 
                PipelineFailureType.LINT, 
                PipelineFailureType.DEPLOY
            ]:
                print("[PIPELINE] → Routing to Coding Agent for implementation fixes")
                return await agent_executor.execute_coding_agent(
                    issue=None,
                    branch=branch,
                    fix_mode=True,
                    error_context=error_details
                )
            
            else:
                print(f"[PIPELINE] ⚠️ Unknown failure type: {failure_type.value}")
                # For unknown failures, try coding agent as default
                return await agent_executor.execute_coding_agent(
                    issue=None,
                    branch=branch,
                    fix_mode=True,
                    error_context=f"Unknown pipeline failure: {error_details}"
                )
        
        except Exception as e:
            print(f"[PIPELINE] ❌ Recovery routing failed: {e}")
            return False
    
    def _record_failure(
        self,
        failure_type: PipelineFailureType,
        branch: str,
        error_details: str,
        outcome: str
    ):
        """
        Record pipeline failure for analysis and learning.
        
        Args:
            failure_type: Type of failure
            branch: Branch where failure occurred
            error_details: Error details
            outcome: Outcome of recovery attempt
        """
        from datetime import datetime
        
        failure_record = {
            "timestamp": datetime.now(),
            "failure_type": failure_type.value,
            "branch": branch,
            "error_details": error_details,
            "outcome": outcome,
            "retry_count": self.retry_counts.get(f"{branch}_{failure_type.value}", 0)
        }
        
        self.failure_history.append(failure_record)
        
        # Keep only recent failures (last 100)
        if len(self.failure_history) > 100:
            self.failure_history = self.failure_history[-100:]
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about pipeline failures and recovery.
        
        Returns:
            Dict containing failure statistics
        """
        if not self.failure_history:
            return {
                "total_failures": 0,
                "recovery_rate": 0.0,
                "most_common_failures": [],
                "branch_failure_counts": {}
            }
        
        total_failures = len(self.failure_history)
        recovered_failures = len([f for f in self.failure_history if f["outcome"] == "recovered"])
        recovery_rate = recovered_failures / total_failures
        
        # Count failure types
        failure_type_counts = {}
        branch_failure_counts = {}
        
        for failure in self.failure_history:
            # Count by failure type
            ft = failure["failure_type"]
            failure_type_counts[ft] = failure_type_counts.get(ft, 0) + 1
            
            # Count by branch
            branch = failure["branch"]
            branch_failure_counts[branch] = branch_failure_counts.get(branch, 0) + 1
        
        # Sort by frequency
        most_common_failures = sorted(
            failure_type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "total_failures": total_failures,
            "recovered_failures": recovered_failures,
            "recovery_rate": recovery_rate,
            "most_common_failures": most_common_failures,
            "branch_failure_counts": branch_failure_counts,
            "current_retry_counts": dict(self.retry_counts)
        }
    
    def get_failure_patterns(self) -> Dict[str, Any]:
        """
        Analyze failure patterns for insights.
        
        Returns:
            Dict containing failure pattern analysis
        """
        if not self.failure_history:
            return {"patterns": [], "recommendations": []}
        
        patterns = []
        recommendations = []
        
        # Analyze recent failures
        recent_failures = self.failure_history[-20:]  # Last 20 failures
        
        # Pattern 1: Repeated failures on same branch
        branch_counts = {}
        for failure in recent_failures:
            branch = failure["branch"]
            branch_counts[branch] = branch_counts.get(branch, 0) + 1
        
        for branch, count in branch_counts.items():
            if count >= 3:
                patterns.append(f"Branch {branch} has {count} recent failures")
                recommendations.append(f"Review branch {branch} for systemic issues")
        
        # Pattern 2: Specific failure type dominance
        type_counts = {}
        for failure in recent_failures:
            ft = failure["failure_type"]
            type_counts[ft] = type_counts.get(ft, 0) + 1
        
        total_recent = len(recent_failures)
        for failure_type, count in type_counts.items():
            if count / total_recent > 0.4:  # > 40% of recent failures
                patterns.append(f"{failure_type} represents {count}/{total_recent} recent failures")
                if failure_type == PipelineFailureType.TESTS.value:
                    recommendations.append("Focus on improving test quality and stability")
                elif failure_type == PipelineFailureType.BUILD.value:
                    recommendations.append("Review build configuration and dependencies")
                elif failure_type == PipelineFailureType.LINT.value:
                    recommendations.append("Improve code quality standards and tooling")
        
        # Pattern 3: Low recovery rate
        recent_recovery_rate = len([f for f in recent_failures if f["outcome"] == "recovered"]) / total_recent
        if recent_recovery_rate < 0.6:  # < 60% recovery rate
            patterns.append(f"Low recent recovery rate: {recent_recovery_rate:.1%}")
            recommendations.append("Review and improve recovery strategies")
        
        return {
            "patterns": patterns,
            "recommendations": recommendations,
            "recent_recovery_rate": recent_recovery_rate if 'recent_recovery_rate' in locals() else 0.0
        }
    
    def reset_retry_counts(self, branch: Optional[str] = None):
        """
        Reset retry counts for a specific branch or all branches.
        
        Args:
            branch: Specific branch to reset, or None for all branches
        """
        if branch:
            # Reset only for specific branch
            keys_to_remove = [k for k in self.retry_counts.keys() if k.startswith(f"{branch}_")]
            for key in keys_to_remove:
                del self.retry_counts[key]
            print(f"[PIPELINE] Reset retry counts for branch: {branch}")
        else:
            # Reset all retry counts
            self.retry_counts = {}
            print("[PIPELINE] Reset all retry counts")
    
    def is_branch_healthy(self, branch: str) -> bool:
        """
        Check if a branch is considered healthy (low failure rate).
        
        Args:
            branch: Branch to check
            
        Returns:
            bool: True if branch is healthy, False if problematic
        """
        # Check recent failures for this branch
        recent_failures = [
            f for f in self.failure_history[-20:]  # Last 20 failures
            if f["branch"] == branch
        ]
        
        if len(recent_failures) == 0:
            return True  # No recent failures
        
        # Check current retry counts
        branch_retry_keys = [k for k in self.retry_counts.keys() if k.startswith(f"{branch}_")]
        total_retries = sum(self.retry_counts[k] for k in branch_retry_keys)
        
        # Branch is unhealthy if it has many recent failures or high retry counts
        return len(recent_failures) < 3 and total_retries < self.max_retries