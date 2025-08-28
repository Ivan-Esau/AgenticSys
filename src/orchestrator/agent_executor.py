"""
Agent execution coordinator for the supervisor orchestrator.
Handles the actual execution of agents with proper error handling and state management.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.core.llm.utils import extract_json_block
from ..agents import (
    planning_agent,
    coding_agent,
    testing_agent,
    review_agent
)


class AgentExecutor:
    """
    Coordinates the execution of individual agents.
    Handles agent invocation, error recovery, and result processing.
    """
    
    def __init__(self, project_id: str, state_manager: Any, tools: List[Any]):
        self.project_id = project_id
        self.state_manager = state_manager
        self.tools = tools
        
        # Execution tracking
        self.current_executions = {}
        self.execution_history = []
    
    async def execute_planning_agent(
        self,
        apply: bool = False,
        show_tokens: bool = True
    ) -> bool:
        """
        Execute planning agent and update state.
        
        Args:
            apply: Whether to apply changes (implementation mode)
            show_tokens: Whether to show token streaming
            
        Returns:
            bool: True if planning successful, False otherwise
        """
        execution_id = self._start_execution_tracking("planning", {"apply": apply})
        
        try:
            print("\n[AGENT EXECUTOR] 🎯 Executing Planning Agent...")
            
            # Set handoff context for planning
            self.state_manager.set_handoff(
                "supervisor",
                "planning",
                {
                    "task": "analyze_and_plan",
                    "apply": apply,
                    "project_id": self.project_id,
                    "constraints": {
                        "focus": "project_analysis_only",
                        "no_implementation": not apply,
                        "create_plan": True
                    }
                }
            )
            
            # Execute planning agent
            result = await planning_agent.run(
                project_id=self.project_id,
                tools=self.tools,
                apply=apply,
                show_tokens=show_tokens
            )
            
            # Process and validate result
            success = await self._process_planning_result(result)
            
            # Clear handoff context
            self.state_manager.clear_handoff()
            
            self._complete_execution_tracking(execution_id, success, result)
            return success
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] ❌ Planning Agent failed: {e}")
            self.state_manager.clear_handoff()
            self._complete_execution_tracking(execution_id, False, str(e))
            return False
    
    async def execute_coding_agent(
        self,
        issue: Optional[Dict] = None,
        branch: Optional[str] = None,
        fix_mode: bool = False,
        error_context: str = "",
        show_tokens: bool = True
    ) -> bool:
        """
        Execute coding agent for implementation or pipeline fixes.
        
        Args:
            issue: Issue to implement (None for fix mode)
            branch: Branch to work on
            fix_mode: Whether this is a pipeline fix
            error_context: Error context for fix mode
            show_tokens: Whether to show token streaming
            
        Returns:
            bool: True if coding successful, False otherwise
        """
        execution_id = self._start_execution_tracking("coding", {
            "issue_id": issue.get("iid") if issue else None,
            "branch": branch,
            "fix_mode": fix_mode
        })
        
        try:
            if fix_mode:
                print(f"\n[AGENT EXECUTOR] 🔧 Executing Coding Agent (Fix Mode)")
                print(f"[FIX] Branch: {branch}")
                print(f"[FIX] Context: {error_context}")
                issues_list = [f"PIPELINE_FIX: {error_context}"]
            else:
                issue_id = issue.get("iid") if issue else "unknown"
                print(f"\n[AGENT EXECUTOR] 💻 Executing Coding Agent (Issue #{issue_id})")
                print(f"[IMPLEMENTATION] Branch: {branch}")
                print(f"[IMPLEMENTATION] Scope: {issue.get('title', 'Unknown') if issue else 'Fix'}")
                issues_list = [issue.get("title", "")] if issue else [""]
                
                # Update state for regular issue implementation
                if issue:
                    self.state_manager.current_issue = issue_id
                    self.state_manager.current_branch = branch
            
            # Set handoff context
            self.state_manager.set_handoff(
                "supervisor",
                "coding",
                {
                    "issue": issue,
                    "branch": branch,
                    "cached_files": list(self.state_manager.file_cache.keys()) if hasattr(self.state_manager, 'file_cache') else [],
                    "fix_mode": fix_mode,
                    "error_context": error_context
                }
            )
            
            # Execute coding agent
            result = await coding_agent.run(
                project_id=self.project_id,
                work_branch=branch,
                issues=issues_list,
                plan_json=self.state_manager.plan,
                tools=self.tools,
                show_tokens=show_tokens,
                fix_mode=fix_mode,
                error_context=error_context
            )
            
            # Process result
            success = self._process_coding_result(result)
            
            # Clear handoff context
            self.state_manager.clear_handoff()
            
            self._complete_execution_tracking(execution_id, success, result)
            return success
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] ❌ Coding Agent failed: {e}")
            self.state_manager.clear_handoff()
            self._complete_execution_tracking(execution_id, False, str(e))
            return False
    
    async def execute_testing_agent(
        self,
        issue: Optional[Dict] = None,
        branch: Optional[str] = None,
        fix_mode: bool = False,
        error_context: str = "",
        show_tokens: bool = True
    ) -> bool:
        """
        Execute testing agent for test creation or pipeline fixes.
        
        Args:
            issue: Issue being tested (None for fix mode)
            branch: Branch to test
            fix_mode: Whether this is a pipeline fix
            error_context: Error context for fix mode
            show_tokens: Whether to show token streaming
            
        Returns:
            bool: True if testing successful, False otherwise
        """
        execution_id = self._start_execution_tracking("testing", {
            "issue_id": issue.get("iid") if issue else None,
            "branch": branch,
            "fix_mode": fix_mode
        })
        
        try:
            if fix_mode:
                print(f"\n[AGENT EXECUTOR] 🧪 Executing Testing Agent (Fix Mode)")
                print(f"[TEST FIX] Branch: {branch}")
                print(f"[TEST FIX] Context: {error_context}")
            else:
                issue_id = issue.get("iid") if issue else "unknown"
                print(f"\n[AGENT EXECUTOR] 🧪 Executing Testing Agent (Issue #{issue_id})")
                print(f"[TESTING] Branch: {branch}")
                print(f"[TESTING] Focus: Create tests for implementation")
            
            # Set handoff context
            handoff_from = "coding" if not fix_mode else "supervisor"
            self.state_manager.set_handoff(
                handoff_from,
                "testing",
                {
                    "issue": issue,
                    "branch": branch,
                    "implementation_complete": not fix_mode,
                    "fix_mode": fix_mode,
                    "error_context": error_context
                }
            )
            
            # Execute testing agent
            result = await testing_agent.run(
                project_id=self.project_id,
                work_branch=branch,
                plan_json=self.state_manager.plan,
                tools=self.tools,
                show_tokens=show_tokens,
                fix_mode=fix_mode,
                error_context=error_context
            )
            
            # Process result
            success = self._process_testing_result(result)
            
            # Clear handoff context
            self.state_manager.clear_handoff()
            
            self._complete_execution_tracking(execution_id, success, result)
            return success
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] ❌ Testing Agent failed: {e}")
            self.state_manager.clear_handoff()
            self._complete_execution_tracking(execution_id, False, str(e))
            return False
    
    async def execute_review_agent(
        self,
        issue: Dict,
        branch: str,
        show_tokens: bool = True
    ) -> Any:
        """
        Execute review agent to create and merge pull request.
        
        Args:
            issue: Issue to review
            branch: Branch to merge
            show_tokens: Whether to show token streaming
            
        Returns:
            Any: Review result (could be success/failure or pipeline failure info)
        """
        issue_id = issue.get("iid")
        execution_id = self._start_execution_tracking("review", {
            "issue_id": issue_id,
            "branch": branch
        })
        
        try:
            print(f"\n[AGENT EXECUTOR] 🔍 Executing Review Agent (Issue #{issue_id})")
            print(f"[REVIEW] Branch: {branch} → master")
            print(f"[REVIEW] Creating merge request and validating implementation")
            
            # Set handoff context
            self.state_manager.set_handoff(
                "testing",
                "review",
                {
                    "issue": issue,
                    "branch": branch,
                    "tests_complete": True,
                    "ready_to_merge": True
                }
            )
            
            # Execute review agent
            result = await review_agent.run(
                project_id=self.project_id,
                work_branch=branch,
                plan_json=self.state_manager.plan,
                tools=self.tools,
                show_tokens=show_tokens
            )
            
            # Process review result (could be success, failure, or pipeline failure)
            success = self._process_review_result(result, issue_id)
            
            # Clear handoff context
            self.state_manager.clear_handoff()
            
            self._complete_execution_tracking(execution_id, success, result)
            return result  # Return full result for pipeline failure handling
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] ❌ Review Agent failed: {e}")
            self.state_manager.clear_handoff()
            self._complete_execution_tracking(execution_id, False, str(e))
            return False
    
    async def _process_planning_result(self, result: Any) -> bool:
        """Process planning agent result and update state."""
        if not result or not isinstance(result, str):
            print("[AGENT EXECUTOR] ❌ Planning Agent returned invalid result")
            return False
        
        # Extract and validate plan
        plan = extract_json_block(result)
        if not plan:
            print("[AGENT EXECUTOR] ❌ No valid plan found in result")
            return False
        
        # Update state with plan
        self.state_manager.plan = plan
        self.state_manager.issues = plan.get("issues", [])
        self.state_manager.implementation_order = plan.get("implementation_order", [])
        
        print(f"[AGENT EXECUTOR] ✅ Planning complete - {len(self.state_manager.issues)} issues planned")
        return True
    
    def _process_coding_result(self, result: Any) -> bool:
        """Process coding agent result - STRICT completion signal required."""
        if not result:
            print("[AGENT EXECUTOR] ❌ Coding Agent returned empty result")
            return False
        
        # STRICT: Only accept explicit completion signal
        if isinstance(result, str):
            result_lower = result.lower()
            if "coding_phase_complete:" in result_lower:
                print("[AGENT EXECUTOR] ✅ Coding Phase completed successfully")
                return True
            elif "error" in result_lower or "failed" in result_lower:
                print("[AGENT EXECUTOR] ❌ Coding implementation failed")
                return False
            else:
                print(f"[AGENT EXECUTOR] ❌ Coding Agent did not provide completion signal")
                print(f"[AGENT EXECUTOR] Expected: 'CODING_PHASE_COMPLETE: Issue #X...'")
                print(f"[AGENT EXECUTOR] Got: {result[:200]}...")
                return False
        
        print("[AGENT EXECUTOR] ❌ Coding Agent returned non-string result")
        return False
    
    def _process_testing_result(self, result: Any) -> bool:
        """Process testing agent result - STRICT completion signal required."""
        if not result:
            print("[AGENT EXECUTOR] ❌ Testing Agent returned empty result")
            return False
        
        # STRICT: Only accept explicit completion signal
        if isinstance(result, str):
            result_lower = result.lower()
            if "testing_phase_complete:" in result_lower:
                print("[AGENT EXECUTOR] ✅ Testing Phase completed successfully")
                return True
            elif "tests_failed:" in result_lower:
                print("[AGENT EXECUTOR] ⚠️ Testing failed but continuing to Review")
                return True  # Allow continuation with test failures
            elif "error" in result_lower or "failed" in result_lower:
                print("[AGENT EXECUTOR] ❌ Testing implementation failed")
                return False
            else:
                print(f"[AGENT EXECUTOR] ❌ Testing Agent did not provide completion signal")
                print(f"[AGENT EXECUTOR] Expected: 'TESTING_PHASE_COMPLETE: Issue #X...'")
                print(f"[AGENT EXECUTOR] Got: {result[:200]}...")
                return False
        
        print("[AGENT EXECUTOR] ❌ Testing Agent returned non-string result")
        return False
    
    def _process_review_result(self, result: Any, issue_id: Any) -> bool:
        """Process review agent result - STRICT completion signal required."""
        if not result:
            print("[AGENT EXECUTOR] ❌ Review Agent returned empty result")
            return False
        
        # STRICT: Only accept explicit completion signals
        if isinstance(result, str):
            result_lower = result.lower()
            if "review_phase_complete:" in result_lower:
                print(f"[AGENT EXECUTOR] ✅ Review Phase completed - Issue #{issue_id} merged and closed")
                return True
            elif "pipeline_failed_" in result:
                print(f"[AGENT EXECUTOR] 🚨 Pipeline failure detected: {result}")
                return False  # This will trigger pipeline failure handling
            elif "error" in result_lower or "failed" in result_lower:
                print("[AGENT EXECUTOR] ❌ Review implementation failed")
                return False
            else:
                print(f"[AGENT EXECUTOR] ❌ Review Agent did not provide completion signal")
                print(f"[AGENT EXECUTOR] Expected: 'REVIEW_PHASE_COMPLETE: Issue #{issue_id}...'")
                print(f"[AGENT EXECUTOR] Got: {result[:200]}...")
                return False
        
        print("[AGENT EXECUTOR] ❌ Review Agent returned non-string result")
        return False
    
    def _start_execution_tracking(self, agent_type: str, params: Dict[str, Any]) -> str:
        """Start tracking an agent execution."""
        execution_id = f"{agent_type}_{int(datetime.now().timestamp() * 1000)}"
        
        execution_info = {
            "execution_id": execution_id,
            "agent_type": agent_type,
            "start_time": datetime.now(),
            "end_time": None,
            "success": None,
            "parameters": params,
            "result": None
        }
        
        self.current_executions[execution_id] = execution_info
        return execution_id
    
    def _complete_execution_tracking(
        self,
        execution_id: str,
        success: bool,
        result: Any
    ):
        """Complete tracking for an agent execution."""
        if execution_id in self.current_executions:
            execution_info = self.current_executions[execution_id]
            execution_info["end_time"] = datetime.now()
            execution_info["success"] = success
            execution_info["result"] = str(result)[:200] if result else None  # Truncate for storage
            
            # Move to history
            self.execution_history.append(execution_info)
            del self.current_executions[execution_id]
            
            # Keep only recent history (last 100 executions)
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
    
    def get_execution_status(self) -> Dict[str, Any]:
        """
        Get current execution status.
        
        Returns:
            Dict containing execution status information
        """
        return {
            "active_executions": len(self.current_executions),
            "current_agents": [
                {
                    "agent": info["agent_type"],
                    "duration": (datetime.now() - info["start_time"]).total_seconds(),
                    "parameters": info["parameters"]
                }
                for info in self.current_executions.values()
            ],
            "recent_completions": [
                {
                    "agent": info["agent_type"],
                    "success": info["success"],
                    "duration": (info["end_time"] - info["start_time"]).total_seconds() if info["end_time"] else 0,
                    "timestamp": info["end_time"]
                }
                for info in self.execution_history[-5:]  # Last 5 completions
            ]
        }
    
    def get_agent_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary for all agents.
        
        Returns:
            Dict containing agent performance metrics
        """
        agent_stats = {}
        
        # Combine current and historical executions
        all_executions = list(self.execution_history)
        
        for execution in all_executions:
            agent = execution["agent_type"]
            if agent not in agent_stats:
                agent_stats[agent] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "total_time": 0.0,
                    "avg_execution_time": 0.0,
                    "success_rate": 0.0
                }
            
            stats = agent_stats[agent]
            stats["total_executions"] += 1
            
            if execution.get("success"):
                stats["successful_executions"] += 1
            else:
                stats["failed_executions"] += 1
            
            # Calculate execution time
            if execution.get("end_time") and execution.get("start_time"):
                duration = (execution["end_time"] - execution["start_time"]).total_seconds()
                stats["total_time"] += duration
        
        # Calculate derived metrics
        for agent, stats in agent_stats.items():
            if stats["total_executions"] > 0:
                stats["success_rate"] = stats["successful_executions"] / stats["total_executions"]
                stats["avg_execution_time"] = stats["total_time"] / stats["total_executions"]
        
        return agent_stats