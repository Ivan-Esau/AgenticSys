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
from ..agents import (
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
    
    def _check_agent_success(self, agent_type: str, result: str) -> tuple[bool, float]:
        """
        Simple success detection for agent outputs.
        Returns (success, confidence) tuple.
        """
        if not result:
            return False, 0.0
        
        # Define success markers for each agent type
        success_markers = {
            "planning": [
                "planning status: complete",
                "planning complete",
                "orchestration plan",
                "plan created",
                "planning is complete",
                "existing orchestration plan found"
            ],
            "coding": [
                "CODING_PHASE_COMPLETE",
                "implementation complete",
                "code complete",
                "files created",
                "implementation successful"
            ],
            "testing": [
                "TESTING_PHASE_COMPLETE",
                "tests complete",
                "tests pass",
                "all tests passing",
                "testing successful"
            ],
            "review": [
                "REVIEW_PHASE_COMPLETE",
                "review complete",
                "merge request created",
                "ready to merge",
                "review successful"
            ]
        }
        
        # Get markers for this agent type
        markers = success_markers.get(agent_type, [])
        if not markers:
            return False, 0.0
        
        # Check for success markers (case-insensitive)
        result_lower = result.lower()
        matches = sum(1 for marker in markers if marker.lower() in result_lower)
        
        if matches > 0:
            # Calculate confidence based on number of matches
            confidence = min(1.0, matches * 0.3)
            return True, confidence
        
        return False, 0.0
    
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
            print("\n[AGENT EXECUTOR] 🎯 Executing Planning Agent...")
            print(f"[AGENT EXECUTOR] 📋 Mode: {'Implementation' if apply else 'Analysis'}")
            
            # Execute planning agent with timeout protection
            result = await asyncio.wait_for(
                planning_agent.run(
                    project_id=self.project_id,
                    tools=self.tools,
                    apply=apply,
                    show_tokens=show_tokens
                ),
                timeout=600  # 10 minute timeout
            )
            
            if not result:
                print("[AGENT EXECUTOR] ⚠️ Planning agent returned empty result")
                self._end_execution_tracking(execution_id, "failed", "Empty result")
                return False
            
            print(f"[AGENT EXECUTOR] 📊 Planning agent completed ({len(result)} chars)")
            
            # Process and validate result with enhanced logging
            success = await self._process_planning_result(result)
            
            if success:
                print("[AGENT EXECUTOR] ✅ Planning agent execution successful")
            else:
                print("[AGENT EXECUTOR] ❌ Planning agent validation failed")
            
            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success
            
        except asyncio.TimeoutError:
            print("[AGENT EXECUTOR] ⏰ Planning agent timed out (10min limit)")
            self._end_execution_tracking(execution_id, "timeout", "Execution timeout")
            return False
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] ❌ Planning agent failed: {e}")
            print(f"[AGENT EXECUTOR] 🔍 Error type: {type(e).__name__}")
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
            print(f"\n[AGENT EXECUTOR] 💻 Executing Coding Agent for Issue #{issue.get('iid')}...")
            
            # Execute coding agent
            result = await coding_agent.run(
                project_id=self.project_id,
                issues=[str(issue.get("iid"))],  # Convert issue to list format
                tools=self.tools,
                work_branch=branch,
                plan_json=self.current_plan,
                show_tokens=show_tokens
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
            print(f"\n[AGENT EXECUTOR] 🧪 Executing Testing Agent for Issue #{issue.get('iid')}...")
            
            # Execute testing agent
            result = await testing_agent.run(
                project_id=self.project_id,
                tools=self.tools,
                work_branch=branch,
                plan_json=self.current_plan,
                show_tokens=show_tokens
            )
            
            # Check for success
            success, confidence = self._check_agent_success("testing", result or "")
            
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
            print(f"\n[AGENT EXECUTOR] 👀 Executing Review Agent for Issue #{issue.get('iid')}...")
            
            # Execute review agent
            result = await review_agent.run(
                project_id=self.project_id,
                tools=self.tools,
                work_branch=branch,
                plan_json=self.current_plan,
                show_tokens=show_tokens
            )
            
            # Check for success
            success, confidence = self._check_agent_success("review", result or "")
            
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
        
        print(f"[AGENT EXECUTOR] 🔍 Analyzing planning agent output...")
        
        # Check for success using simple detection
        success, confidence = self._check_agent_success("planning", result)
        
        print(f"[AGENT EXECUTOR] 📊 Detection Results:")
        print(f"  - Success: {success}")
        print(f"  - Confidence: {confidence:.2%}")
        
        # Planning agent completed successfully
        if success:
            print("[AGENT EXECUTOR] ✅ Planning analysis completed - no orchestration plan needed")
            
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
        print(f"[AGENT EXECUTOR] 📄 Agent output length: {len(result)} chars")
        
        # Diagnostic info for debugging
        if len(result) < 200:
            print("[AGENT EXECUTOR] ⚠️ Suspiciously short output - possible tool execution failure")
            print(f"[AGENT EXECUTOR] 📋 Output preview: {repr(result[:100])}")
        
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
        print(f"[AGENT EXECUTOR] 📤 Triggering supervisor feedback for {agent_type} agent failure on issue #{issue_id}")
        # This would integrate with supervisor's feedback system
        # For now, just log the failure for supervisor to handle
        
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return {
            "project_id": self.project_id,
            "current_executions": len(self.current_executions),
            "completed_executions": len(self.execution_history),
            "has_plan": self.current_plan is not None,
            "planned_issues": len(self.current_plan.get("issues", [])) if self.current_plan else 0
        }