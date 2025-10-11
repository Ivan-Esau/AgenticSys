"""
Agent execution coordinator for the supervisor orchestrator.
Handles the actual execution of agents with proper error handling.
Uses flexible success detection system for robust operation.
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from pathlib import Path

from src.core.llm.utils import extract_json_block
from ..utils import CompletionMarkers
from ...agents import (
    planning_agent,
    coding_agent,
    testing_agent,
    review_agent
)


class AgentExecutor:
    """
    Coordinates the execution of individual agents.
    Uses flexible success detection for robust operation.
    """

    def __init__(self, project_id: str, tools: List[Any], output_callback=None):
        self.project_id = project_id
        self.tools = tools
        self.output_callback = output_callback  # Optional WebSocket callback

        # Execution tracking
        self.current_executions = {}
        self.execution_history = []
        self.current_plan = None

        # Tech stack configuration (set by supervisor)
        self.tech_stack = None  # Will be set by supervisor
        self.debugging_context = None

        # Pipeline tracking between agents (CRITICAL FIX for PIPELINE_WAITING_FIX.md)
        # Testing Agent creates the pipeline for the feature branch
        # Review Agent MUST validate the SAME pipeline (not a different/older one)
        self.testing_pipeline_id = None  # Testing Agent's pipeline ID (source of truth)
        self.current_pipeline_id = None  # Review Agent's pipeline ID (must match above!)

        # Analytics tracking (set by supervisor)
        self.issue_tracker = None  # Will be set by supervisor per issue
    
    def _check_agent_success(self, agent_type: str, result: str) -> tuple[bool, float]:
        """
        Check agent success using centralized completion markers.
        Returns (success, confidence) tuple.

        CRITICAL: Pipeline failure detection is agent-aware:
        - Coding agent: Only fail on COMPILATION_FAILED (ignore test failures)
        - Testing agent: Fail on TESTS_FAILED or PIPELINE_FAILED
        - Review agent: Fail on PIPELINE_FAILED or MERGE_BLOCKED
        """
        if not result:
            return False, 0.0

        # Agent-specific failure detection
        if agent_type == "coding":
            # Coding agent: ONLY fail on compilation errors
            if "COMPILATION_FAILED" in result:
                print(f"[AGENT EXECUTOR] [FAIL] Compilation failure detected")
                return False, 0.0

            # IGNORE any mentions of test failures or general pipeline failures
            # (Testing agent will handle those)

        elif agent_type in ["testing", "review"]:
            # Testing/Review agents: fail on pipeline failures
            if CompletionMarkers.has_pipeline_failure(result):
                failure_type = CompletionMarkers.get_pipeline_failure_type(result)
                print(f"[AGENT EXECUTOR] [FAIL] Pipeline failure detected: {failure_type}")

                # Check if this is a network failure that should be retried
                if CompletionMarkers.should_retry_pipeline(result):
                    print(f"[AGENT EXECUTOR] Network failure - pipeline retry recommended")

                # Pipeline failure means task failed
                return False, 0.0

        # Check for completion markers
        success, confidence, reason = CompletionMarkers.check_completion(agent_type, result)

        # Log the detection reason for debugging
        if success:
            print(f"[AGENT EXECUTOR] [OK] Success detected: {reason}")
        elif confidence > 0:
            print(f"[AGENT EXECUTOR] [WARN] Partial match: {reason}")

        return success, confidence

    def _extract_pipeline_id(self, agent_output: str) -> Optional[str]:
        """
        Extract pipeline ID from agent output.
        Looks for patterns like:
        - "Created MY pipeline: #4259"
        - "Monitoring pipeline: #4259"
        - "Pipeline #4259"
        """
        import re

        # Look for various pipeline ID patterns
        patterns = [
            r"Created MY pipeline:\s*#(\d+)",  # Testing agent pattern
            r"Monitoring pipeline:\s*#(\d+)",   # Review agent pattern
            r"MY_PIPELINE_ID\s*=\s*['\"]?(\d+)", # Variable assignment
            r"CURRENT_PIPELINE_ID\s*=\s*['\"]?(\d+)", # Review agent variable
            r"Pipeline\s+#(\d+)\s+(?:status|completed)", # General pipeline mention
        ]

        for pattern in patterns:
            match = re.search(pattern, agent_output, re.IGNORECASE)
            if match:
                pipeline_id = match.group(1)
                print(f"[AGENT EXECUTOR] Extracted pipeline ID: #{pipeline_id}")
                return pipeline_id

        return None
    
    async def execute_planning_agent(
        self,
        apply: bool = False,
        show_tokens: bool = True
    ) -> bool:
        """
        Execute planning agent with robust error handling and retry logic.
        """
        execution_id = self._start_execution_tracking("planning", {"apply": apply})

        # Track agent start in issue tracker
        if self.issue_tracker:
            self.issue_tracker.start_agent('planning')

        try:
            print("\n[AGENT EXECUTOR] Executing Planning Agent...")
            print(f"[AGENT EXECUTOR] Mode: {'Implementation' if apply else 'Analysis'}")

            # Agents will monitor their own pipelines via MCP tools

            # Execute planning agent with timeout protection
            result = await asyncio.wait_for(
                planning_agent.run(
                    project_id=self.project_id,
                    tools=self.tools,
                    apply=apply,
                    show_tokens=show_tokens,
                    pipeline_config=self.tech_stack,
                    output_callback=self.output_callback
                ),
                timeout=600  # 10 minute timeout
            )
            
            if not result:
                print("[AGENT EXECUTOR] WARNING: Planning agent returned empty result")
                self._end_execution_tracking(execution_id, "failed", "Empty result")
                return False
            
            print(f"[AGENT EXECUTOR] Planning agent completed ({len(result)} chars)")
            
            # Process and validate result with enhanced logging
            success = await self._process_planning_result(result)
            
            if success:
                print("[AGENT EXECUTOR] Planning agent execution successful")
            else:
                print("[AGENT EXECUTOR] Planning agent validation failed")

            # Track agent end in issue tracker
            if self.issue_tracker:
                self.issue_tracker.end_agent('planning', success)

            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success

        except asyncio.TimeoutError:
            print("[AGENT EXECUTOR] Planning agent timed out (10min limit)")
            if self.issue_tracker:
                self.issue_tracker.end_agent('planning', False)
            self._end_execution_tracking(execution_id, "timeout", "Execution timeout")
            return False

        except Exception as e:
            print(f"[AGENT EXECUTOR] Planning agent failed: {e}")
            print(f"[AGENT EXECUTOR] Error type: {type(e).__name__}")
            # Add more debug info for troubleshooting
            import traceback
            if "tool decorator" in str(e):
                print("[AGENT EXECUTOR] Tool compatibility issue detected")
                print("[AGENT EXECUTOR] This may be due to MCP tool format incompatibility")
            if self.issue_tracker:
                self.issue_tracker.end_agent('planning', False)
            self._end_execution_tracking(execution_id, "error", str(e))
            return False
    
    async def execute_coding_agent(
        self,
        issue: Dict[str, Any],
        branch: str,
        show_tokens: bool = True
    ) -> bool:
        """
        Execute coding agent for a specific issue.
        """
        execution_id = self._start_execution_tracking("coding", {"issue_iid": issue.get("iid"), "branch": branch})

        # Track agent start in issue tracker
        if self.issue_tracker:
            self.issue_tracker.start_agent('coding')

        try:
            print(f"\n[AGENT EXECUTOR] Executing Coding Agent for Issue #{issue.get('iid')}...")
            
            # Execute coding agent
            result = await coding_agent.run(
                project_id=self.project_id,
                issues=[str(issue.get("iid"))],  # Convert issue to list format
                tools=self.tools,
                work_branch=branch,
                plan_json=self.current_plan,
                show_tokens=show_tokens,
                pipeline_config=self.tech_stack,
                output_callback=self.output_callback
            )
            
            # Check for success
            success, confidence = self._check_agent_success("coding", result or "")

            # Track agent end in issue tracker
            if self.issue_tracker:
                self.issue_tracker.end_agent('coding', success)

            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success

        except Exception as e:
            print(f"[AGENT EXECUTOR] [FAIL] Coding agent failed: {e}")
            if self.issue_tracker:
                self.issue_tracker.end_agent('coding', False)
            self._end_execution_tracking(execution_id, "error", str(e))
            return False
    
    async def execute_testing_agent(
        self,
        issue: Dict[str, Any],
        branch: str,
        show_tokens: bool = True
    ) -> bool:
        """
        Execute testing agent for a specific issue.
        """
        execution_id = self._start_execution_tracking("testing", {"issue_iid": issue.get("iid"), "branch": branch})

        # Track agent start in issue tracker
        if self.issue_tracker:
            self.issue_tracker.start_agent('testing')

        try:
            print(f"\n[AGENT EXECUTOR] Executing Testing Agent for Issue #{issue.get('iid')}...")

            # Testing agent monitors pipeline via MCP tools

            # Execute testing agent
            result = await testing_agent.run(
                project_id=self.project_id,
                tools=self.tools,
                work_branch=branch,
                plan_json=self.current_plan,
                show_tokens=show_tokens,
                pipeline_config=self.tech_stack,
                output_callback=self.output_callback
            )
            
            # Check for success
            success, confidence = self._check_agent_success("testing", result or "")

            # Extract and store Testing Agent's pipeline ID (KEY FIX)
            if result:
                pipeline_id = self._extract_pipeline_id(result)
                if pipeline_id:
                    self.testing_pipeline_id = pipeline_id
                    print(f"[AGENT EXECUTOR] Stored Testing Agent pipeline: #{pipeline_id}")

                    # Track pipeline attempt in issue tracker
                    if self.issue_tracker:
                        self.issue_tracker.record_pipeline_attempt(
                            pipeline_id=pipeline_id,
                            status='success' if success else 'failed',
                            commit_sha=None  # Could extract from result if needed
                        )

            # Track agent end in issue tracker
            if self.issue_tracker:
                self.issue_tracker.end_agent('testing', success)

            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] [FAIL] Testing agent failed: {e}")
            if self.issue_tracker:
                self.issue_tracker.end_agent('testing', False)
            self._end_execution_tracking(execution_id, "error", str(e))
            return False
    
    async def execute_review_agent(
        self,
        issue: Dict[str, Any],
        branch: str,
        show_tokens: bool = True
    ) -> bool:
        """
        Execute review agent for a specific issue.
        """
        execution_id = self._start_execution_tracking("review", {"issue_iid": issue.get("iid"), "branch": branch})

        # Track agent start in issue tracker
        if self.issue_tracker:
            self.issue_tracker.start_agent('review')

        try:
            print(f"\n[AGENT EXECUTOR] Executing Review Agent for Issue #{issue.get('iid')}...")
            
            # Execute review agent
            result = await review_agent.run(
                project_id=self.project_id,
                tools=self.tools,
                work_branch=branch,
                plan_json=self.current_plan,
                show_tokens=show_tokens,
                pipeline_config=self.tech_stack,
                output_callback=self.output_callback
            )
            
            # Check for success - CRITICAL: Must verify pipeline passed
            success, confidence = self._check_agent_success("review", result or "")

            # Extract and validate Review Agent's pipeline ID (KEY FIX)
            if result:
                pipeline_id = self._extract_pipeline_id(result)
                if pipeline_id:
                    self.current_pipeline_id = pipeline_id
                    print(f"[AGENT EXECUTOR] Review Agent monitoring pipeline: #{pipeline_id}")

                    # Check if it matches Testing Agent's pipeline (informational)
                    if self.testing_pipeline_id:
                        if pipeline_id != self.testing_pipeline_id:
                            print(f"[AGENT EXECUTOR] [INFO] Different pipeline detected")
                            print(f"[AGENT EXECUTOR] Testing Agent created: #{self.testing_pipeline_id}")
                            print(f"[AGENT EXECUTOR] Review Agent monitoring: #{pipeline_id}")
                            print(f"[AGENT EXECUTOR] [INFO] This is normal - MR creation triggers a new pipeline")
                            print(f"[AGENT EXECUTOR] [INFO] Both pipelines run the same code - verifying MR pipeline")
                        else:
                            print(f"[AGENT EXECUTOR] [OK] Pipeline ID verified: #{pipeline_id} matches Testing Agent")

            # Additional validation for review agent - must not have pipeline failures
            if success and "REVIEW_PHASE_COMPLETE" in (result or ""):
                # Check for merge completion (both active merge and already-merged cases)
                if "merged and closed successfully" in result or "already completed and merged" in result:
                    # Look for any pipeline status indicators (more flexible)
                    pipeline_indicators = [
                        "pipeline.*success", "pipeline.*passed", "pipeline.*completed",
                        "[OK].*success", "test job.*success", "build job.*success",
                        "pipeline status.*success", "both.*jobs.*passed",
                        "already merged"  # Accept for already-merged case
                    ]

                    import re
                    has_pipeline_confirmation = any(
                        re.search(pattern, result.lower()) for pattern in pipeline_indicators
                    )

                    # For "already merged" case, accept if MR reference is present
                    if "already merged via MR" in result.lower() or "already completed and merged" in result.lower():
                        print(f"[AGENT EXECUTOR] [OK] Review agent confirmed work already merged")
                        has_pipeline_confirmation = True  # Trust that previous merge verified pipeline

                    if has_pipeline_confirmation:
                        print(f"[AGENT EXECUTOR] [OK] Review agent confirmed pipeline success and merge completion")
                    else:
                        # Check if this is likely a legitimate completion by looking for detailed pipeline info
                        if any(phrase in result.lower() for phrase in ["test job", "build job", "pipeline", "jobs.*passed"]):
                            print(f"[AGENT EXECUTOR] [OK] Review agent provided pipeline details - accepting completion")
                        else:
                            print(f"[AGENT EXECUTOR] [WARN] WARNING: Review claimed success but no pipeline details found")
                            print(f"[AGENT EXECUTOR] [FAIL] Blocking merge - pipeline verification missing")
                            success = False
                else:
                    print(f"[AGENT EXECUTOR] [WARN] WARNING: Review claimed completion but no merge confirmation")
                    success = False

            # Track agent end in issue tracker
            if self.issue_tracker:
                self.issue_tracker.end_agent('review', success)

            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success

        except Exception as e:
            print(f"[AGENT EXECUTOR] [FAIL] Review agent failed: {e}")
            if self.issue_tracker:
                self.issue_tracker.end_agent('review', False)
            self._end_execution_tracking(execution_id, "error", str(e))
            return False
    
    async def _process_planning_result(self, result: str) -> bool:
        """
        Process planning agent result using flexible success detection.
        REQUIRES baseline verification for planning agent.
        """
        if not result:
            print("[AGENT EXECUTOR] [FAIL] No result from planning agent")
            return False

        print(f"[AGENT EXECUTOR] Analyzing planning agent output...")

        # CRITICAL: Check for BASELINE_VERIFIED signal (mandatory for planning)
        has_baseline_verified = "baseline_verified" in result.lower()

        # CRITICAL: Verify pipeline actually PASSED (not just "running")
        import re
        pipeline_passed = False
        if has_baseline_verified:
            # Check for "passed successfully" or "status: success" or "completed: success"
            passed_patterns = [
                r"pipeline.*#\d+.*passed successfully",
                r"pipeline.*#\d+.*status.*success",
                r"pipeline.*#\d+.*completed.*success"
            ]
            for pattern in passed_patterns:
                if re.search(pattern, result.lower()):
                    pipeline_passed = True
                    break

            # Reject if says "running" or "pending"
            if re.search(r"pipeline.*#\d+.*is running", result.lower()):
                print("[AGENT EXECUTOR] [FAIL] Pipeline is still RUNNING - not SUCCESS!")
                pipeline_passed = False
            if re.search(r"pipeline.*#\d+.*is pending", result.lower()):
                print("[AGENT EXECUTOR] [FAIL] Pipeline is still PENDING - not SUCCESS!")
                pipeline_passed = False

        # Check for success using simple detection
        success, confidence = self._check_agent_success("planning", result)

        print(f"[AGENT EXECUTOR] Detection Results:")
        print(f"  - Success: {success}")
        print(f"  - Confidence: {confidence:.2%}")
        print(f"  - Baseline Verified: {has_baseline_verified}")
        print(f"  - Pipeline Passed: {pipeline_passed}")

        # Check if ORCH_PLAN already exists (indicates previous successful planning)
        has_existing_plan = "orch_plan.json" in result.lower() and "already exists" in result.lower()
        if has_existing_plan:
            print("[AGENT EXECUTOR] [INFO] ORCH_PLAN already exists from previous run")

        # Baseline verification is OPTIONAL if:
        # 1. An ORCH_PLAN.json already exists (previous successful planning), OR
        # 2. Agent explicitly states baseline was verified
        if success:
            if has_baseline_verified and pipeline_passed:
                print("[AGENT EXECUTOR] [OK] Planning analysis completed WITH baseline verification")
            elif has_existing_plan:
                print("[AGENT EXECUTOR] [OK] Planning analysis using existing ORCH_PLAN (baseline verification skipped)")
            elif not has_baseline_verified:
                print("[AGENT EXECUTOR] [WARN] Planning completed without baseline verification")
                print("[AGENT EXECUTOR] [INFO] Accepting result as planning analysis is complete")

            # Warn if baseline was claimed but pipeline didn't pass
            if has_baseline_verified and not pipeline_passed:
                print("[AGENT EXECUTOR] [WARN] Baseline verification claimed but pipeline not confirmed passed")
                print("[AGENT EXECUTOR] [INFO] Accepting result - coding phase will verify build")

            # Store the planning analysis result for supervisor use
            if result and not self.current_plan:
                self.current_plan = result  # Store the full planning analysis text
                print("[AGENT EXECUTOR] Stored planning analysis for issue prioritization")

            print("[AGENT EXECUTOR] [OK] Planning agent execution successful")
            return True
        
        # Fallback: Try JSON extraction even if detection failed
        if confidence > 0.3:  # Some positive signals detected
            try:
                json_block = extract_json_block(result)
                if json_block:
                    plan = json.loads(json_block)
                    self.current_plan = plan
                    print(f"[AGENT EXECUTOR] [OK] Planning succeeded (JSON plan extracted as fallback)")
                    return True
            except Exception as e:
                print(f"[AGENT EXECUTOR] [WARN] JSON extraction fallback failed: {e}")
        
        print(f"[AGENT EXECUTOR] [FAIL] Planning validation failed")
        print(f"[AGENT EXECUTOR] Agent output length: {len(result)} chars")
        
        # Diagnostic info for debugging
        if len(result) < 200:
            print("[AGENT EXECUTOR] [WARN] Suspiciously short output - possible tool execution failure")
            print(f"[AGENT EXECUTOR] Output preview: {repr(result[:100])}")
        
        return False
    
    
    def _start_execution_tracking(self, agent_type: str, context: Dict[str, Any]) -> str:
        """Start tracking an agent execution."""
        execution_id = f"{agent_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_executions[execution_id] = {
            "agent_type": agent_type,
            "start_time": datetime.now(),
            "context": context,
            "status": "running"
        }
        return execution_id
    
    def _end_execution_tracking(self, execution_id: str, status: str, error_msg: str = None):
        """End tracking an agent execution."""
        if execution_id in self.current_executions:
            execution = self.current_executions[execution_id]
            execution["end_time"] = datetime.now()
            execution["status"] = status
            if error_msg:
                execution["error"] = error_msg
            
            # Move to history
            self.execution_history.append(execution)
            del self.current_executions[execution_id]
    
    def _trigger_supervisor_feedback(self, agent_type: str, failure_message: str, issue_iid: str, context: dict = None):
        """Trigger supervisor feedback for agent failures."""
        print(f"[AGENT EXECUTOR] Triggering supervisor feedback for {agent_type} agent failure on issue #{issue_iid}")
        # This would integrate with supervisor's feedback system
        # For now, just log the failure for supervisor to handle
        
    
    def reset_pipeline_tracking(self):
        """
        Reset pipeline tracking for new issue.
        Called by supervisor before starting work on a new issue.
        """
        if self.testing_pipeline_id or self.current_pipeline_id:
            print(f"[AGENT EXECUTOR] Resetting pipeline tracking (previous: Testing #{self.testing_pipeline_id}, Review #{self.current_pipeline_id})")
        self.testing_pipeline_id = None
        self.current_pipeline_id = None

    def get_pipeline_tracking_status(self) -> Dict[str, Any]:
        """Get current pipeline tracking status for debugging."""
        return {
            "testing_pipeline_id": self.testing_pipeline_id,
            "current_pipeline_id": self.current_pipeline_id,
            "pipelines_match": (
                self.testing_pipeline_id == self.current_pipeline_id
                if self.testing_pipeline_id and self.current_pipeline_id
                else None
            )
        }

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return {
            "project_id": self.project_id,
            "current_executions": len(self.current_executions),
            "completed_executions": len(self.execution_history),
            "has_plan": self.current_plan is not None,
            "planned_issues": len(self.current_plan.get("issues", [])) if isinstance(self.current_plan, dict) else 0,
            "pipeline_tracking": self.get_pipeline_tracking_status()
        }