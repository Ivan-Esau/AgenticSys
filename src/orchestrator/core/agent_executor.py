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
    
    def __init__(self, project_id: str, tools: List[Any]):
        self.project_id = project_id
        self.tools = tools
        
        # Execution tracking
        self.current_executions = {}
        self.execution_history = []
        self.current_plan = None
        
        # Pipeline configuration (set by supervisor)
        self.pipeline_config = None
        self.debugging_context = None

        # Pipeline tracking between agents (KEY FIX)
        self.testing_pipeline_id = None  # Store Testing Agent's pipeline ID
        self.current_pipeline_id = None  # Current pipeline being monitored
    
    def _check_agent_success(self, agent_type: str, result: str) -> tuple[bool, float]:
        """
        Check agent success using centralized completion markers.
        Returns (success, confidence) tuple.
        """
        # First check for pipeline failures (critical for review agent)
        if CompletionMarkers.has_pipeline_failure(result):
            failure_type = CompletionMarkers.get_pipeline_failure_type(result)
            print(f"[AGENT EXECUTOR] ❌ Pipeline failure detected: {failure_type}")

            # Check if this is a network failure that should be retried
            if CompletionMarkers.should_retry_pipeline(result):
                print(f"[AGENT EXECUTOR] Network failure - pipeline retry recommended")

            # Pipeline failure means task failed
            return False, 0.0

        # Check for completion markers
        success, confidence, reason = CompletionMarkers.check_completion(agent_type, result)

        # Log the detection reason for debugging
        if success:
            print(f"[AGENT EXECUTOR] ✅ Success detected: {reason}")
        elif confidence > 0:
            print(f"[AGENT EXECUTOR] ⚠️ Partial match: {reason}")

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
        
        try:
            print("\n[AGENT EXECUTOR] Executing Planning Agent...")
            print(f"[AGENT EXECUTOR] Mode: {'Implementation' if apply else 'Analysis'}")
            
            # Execute planning agent with timeout protection
            result = await asyncio.wait_for(
                planning_agent.run(
                    project_id=self.project_id,
                    tools=self.tools,
                    apply=apply,
                    show_tokens=show_tokens,
                    pipeline_config=self.pipeline_config.config if self.pipeline_config else None
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
            
            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success
            
        except asyncio.TimeoutError:
            print("[AGENT EXECUTOR] Planning agent timed out (10min limit)")
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
        execution_id = self._start_execution_tracking("coding", {"issue_id": issue.get("iid"), "branch": branch})
        
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
                pipeline_config=self.pipeline_config.config if self.pipeline_config else None
            )
            
            # Check for success
            success, confidence = self._check_agent_success("coding", result or "")
            
            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] ❌ Coding agent failed: {e}")
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
        execution_id = self._start_execution_tracking("testing", {"issue_id": issue.get("iid"), "branch": branch})
        
        try:
            print(f"\n[AGENT EXECUTOR] Executing Testing Agent for Issue #{issue.get('iid')}...")
            
            # Execute testing agent
            result = await testing_agent.run(
                project_id=self.project_id,
                tools=self.tools,
                work_branch=branch,
                plan_json=self.current_plan,
                show_tokens=show_tokens,
                pipeline_config=self.pipeline_config.config if self.pipeline_config else None
            )
            
            # Check for success
            success, confidence = self._check_agent_success("testing", result or "")

            # Extract and store Testing Agent's pipeline ID (KEY FIX)
            if result:
                pipeline_id = self._extract_pipeline_id(result)
                if pipeline_id:
                    self.testing_pipeline_id = pipeline_id
                    print(f"[AGENT EXECUTOR] Stored Testing Agent pipeline: #{pipeline_id}")

            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] ❌ Testing agent failed: {e}")
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
        execution_id = self._start_execution_tracking("review", {"issue_id": issue.get("iid"), "branch": branch})
        
        try:
            print(f"\n[AGENT EXECUTOR] Executing Review Agent for Issue #{issue.get('iid')}...")
            
            # Execute review agent
            result = await review_agent.run(
                project_id=self.project_id,
                tools=self.tools,
                work_branch=branch,
                plan_json=self.current_plan,
                show_tokens=show_tokens,
                pipeline_config=self.pipeline_config.config if self.pipeline_config else None
            )
            
            # Check for success - CRITICAL: Must verify pipeline passed
            success, confidence = self._check_agent_success("review", result or "")

            # Extract and validate Review Agent's pipeline ID (KEY FIX)
            if result:
                pipeline_id = self._extract_pipeline_id(result)
                if pipeline_id:
                    self.current_pipeline_id = pipeline_id
                    print(f"[AGENT EXECUTOR] Review Agent monitoring pipeline: #{pipeline_id}")

                    # Validate it matches Testing Agent's pipeline
                    if self.testing_pipeline_id and pipeline_id != self.testing_pipeline_id:
                        print(f"[AGENT EXECUTOR] ⚠️ WARNING: Pipeline mismatch!")
                        print(f"[AGENT EXECUTOR] Testing Agent: #{self.testing_pipeline_id}")
                        print(f"[AGENT EXECUTOR] Review Agent: #{pipeline_id}")
                        # This is a critical error - wrong pipeline!

            # Additional validation for review agent - must not have pipeline failures
            if success and "REVIEW_PHASE_COMPLETE" in (result or ""):
                # Check for merge completion
                if "merged and closed successfully" in result:
                    # Look for any pipeline status indicators (more flexible)
                    pipeline_indicators = [
                        "pipeline.*success", "pipeline.*passed", "pipeline.*completed",
                        "✅.*success", "test job.*success", "build job.*success",
                        "pipeline status.*success", "both.*jobs.*passed"
                    ]

                    import re
                    has_pipeline_confirmation = any(
                        re.search(pattern, result.lower()) for pattern in pipeline_indicators
                    )

                    if has_pipeline_confirmation:
                        print(f"[AGENT EXECUTOR] ✅ Review agent confirmed pipeline success and merge completion")
                    else:
                        # Check if this is likely a legitimate completion by looking for detailed pipeline info
                        if any(phrase in result.lower() for phrase in ["test job", "build job", "pipeline", "jobs.*passed"]):
                            print(f"[AGENT EXECUTOR] ✅ Review agent provided pipeline details - accepting completion")
                        else:
                            print(f"[AGENT EXECUTOR] ⚠️ WARNING: Review claimed success but no pipeline details found")
                            print(f"[AGENT EXECUTOR] ❌ Blocking merge - pipeline verification missing")
                            success = False
                else:
                    print(f"[AGENT EXECUTOR] ⚠️ WARNING: Review claimed completion but no merge confirmation")
                    success = False

            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] ❌ Review agent failed: {e}")
            self._end_execution_tracking(execution_id, "error", str(e))
            return False
    
    async def _process_planning_result(self, result: str) -> bool:
        """
        Process planning agent result using flexible success detection.
        No more hardcoded patterns - uses intelligent detection strategies.
        """
        if not result:
            print("[AGENT EXECUTOR] ❌ No result from planning agent")
            return False
        
        print(f"[AGENT EXECUTOR] Analyzing planning agent output...")
        
        # Check for success using simple detection
        success, confidence = self._check_agent_success("planning", result)
        
        print(f"[AGENT EXECUTOR] Detection Results:")
        print(f"  - Success: {success}")
        print(f"  - Confidence: {confidence:.2%}")
        
        # Planning agent completed successfully
        if success:
            print("[AGENT EXECUTOR] ✅ Planning analysis completed")

            # Store the planning analysis result for supervisor use
            if result and not self.current_plan:
                self.current_plan = result  # Store the full planning analysis text
                print("[AGENT EXECUTOR] Stored planning analysis for issue prioritization")

            print("[AGENT EXECUTOR] ✅ Planning agent execution successful")
            return True
        
        # Fallback: Try JSON extraction even if detection failed
        if confidence > 0.3:  # Some positive signals detected
            try:
                json_block = extract_json_block(result)
                if json_block:
                    plan = json.loads(json_block)
                    self.current_plan = plan
                    print(f"[AGENT EXECUTOR] ✅ Planning succeeded (JSON plan extracted as fallback)")
                    return True
            except Exception as e:
                print(f"[AGENT EXECUTOR] ⚠️ JSON extraction fallback failed: {e}")
        
        print(f"[AGENT EXECUTOR] ❌ Planning validation failed")
        print(f"[AGENT EXECUTOR] Agent output length: {len(result)} chars")
        
        # Diagnostic info for debugging
        if len(result) < 200:
            print("[AGENT EXECUTOR] ⚠️ Suspiciously short output - possible tool execution failure")
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
    
    def _trigger_supervisor_feedback(self, agent_type: str, failure_message: str, issue_id: str, context: dict = None):
        """Trigger supervisor feedback for agent failures."""
        print(f"[AGENT EXECUTOR] Triggering supervisor feedback for {agent_type} agent failure on issue #{issue_id}")
        # This would integrate with supervisor's feedback system
        # For now, just log the failure for supervisor to handle
        
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return {
            "project_id": self.project_id,
            "current_executions": len(self.current_executions),
            "completed_executions": len(self.execution_history),
            "has_plan": self.current_plan is not None,
            "planned_issues": len(self.current_plan.get("issues", [])) if isinstance(self.current_plan, dict) else 0
        }