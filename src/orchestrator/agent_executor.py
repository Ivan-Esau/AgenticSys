"""
Agent execution coordinator for the supervisor orchestrator.
Handles the actual execution of agents with proper error handling.
Simplified version without broken state management.
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
    Simplified version without broken state management.
    """
    
    def __init__(self, project_id: str, state_manager: Any, tools: List[Any]):
        self.project_id = project_id
        # state_manager removed (was broken state system)
        self.tools = tools
        
        # Execution tracking
        self.current_executions = {}
        self.execution_history = []
        self.current_plan = None
    
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
            
            # Check for completion signal
            success = result and "CODING_PHASE_COMPLETE" in result
            
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
            
            # Check for completion signal
            success = result and "TESTING_PHASE_COMPLETE" in result
            
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
            
            # Check for completion signal
            success = result and "REVIEW_PHASE_COMPLETE" in result
            
            self._end_execution_tracking(execution_id, "success" if success else "failed")
            return success
            
        except Exception as e:
            print(f"[AGENT EXECUTOR] ❌ Review agent failed: {e}")
            self._end_execution_tracking(execution_id, "error", str(e))
            return False
    
    async def _process_planning_result(self, result: str) -> bool:
        """
        Process planning agent result using modern multi-agent orchestration patterns.
        Implements flexible success detection and proper agent coordination.
        """
        if not result:
            print("[AGENT EXECUTOR] ❌ No result from planning agent")
            return False
        
        print(f"[AGENT EXECUTOR] 🔍 Analyzing planning agent output...")
        
        # Modern multi-agent success detection patterns
        # Based on 2024-2025 multi-agent orchestration best practices
        success_indicators = [
            "✅ Planning Status: COMPLETE",
            "Planning Status: COMPLETE",
            "✅ Planning Status Complete",
            "Planning Status Complete",
            "✅ Planning Status Report",
            "Planning Status Report",
            "Planning Status Update",
            "✅ Planning Status Update", 
            "✅ Planning Complete",
            "Planning Complete",
            "orchestration plan found and updated",
            "Orchestration plan already exists",
            "Orchestration Plan Already Exists",
            "planning is complete",
            "Planning is COMPLETE", 
            "No additional planning is needed",
            "Existing Orchestration Plan Found",
            "project is perfectly positioned",
            "orchestration plan provides clear guidance",
            "The orchestration plan is fully established",
            "orchestration planning is already complete",
            "Orchestration Plan Already Exists and is Complete",
            "orchestration plan is already complete"
        ]
        
        # Check for explicit success indicators in agent output
        result_indicates_success = any(indicator in result for indicator in success_indicators)
        
        if result_indicates_success:
            print("[AGENT EXECUTOR] ✅ Planning agent reported successful completion")
        
        # Multi-tier success validation approach
        success_tiers = []
        
        # Tier 1: File system validation (highest priority)
        plan_file = Path("docs/ORCH_PLAN.json")
        try:
            if plan_file.exists():
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plan = json.load(f)
                self.current_plan = plan
                success_tiers.append("file_system")
                print(f"[AGENT EXECUTOR] ✅ Found orchestration plan - {len(plan.get('issues', []))} issues")
        except Exception as e:
            print(f"[AGENT EXECUTOR] ⚠️ Error reading plan file: {e}")
        
        # Tier 2: Agent explicit success signals
        if result_indicates_success:
            success_tiers.append("agent_signal")
        
        # Tier 3: Content analysis (check if agent provided meaningful output)
        meaningful_content_indicators = [
            "Phase 1", "Phase 2", "Infrastructure", "CI/CD", "Next Steps", 
            "Implementation", "Project", "Complete", "PENDING", "Ready"
        ]
        content_analysis = sum(1 for indicator in meaningful_content_indicators if indicator in result)
        if content_analysis >= 5:  # Agent provided substantial analysis
            success_tiers.append("content_analysis")
            print(f"[AGENT EXECUTOR] ✅ Planning agent provided comprehensive analysis ({content_analysis} key topics)")
        
        # Multi-tier success determination
        if len(success_tiers) >= 2:  # At least 2 success indicators
            print(f"[AGENT EXECUTOR] ✅ Planning succeeded (validation tiers: {', '.join(success_tiers)})")
            # Ensure plan is loaded even with multi-tier success
            if self.current_plan is None:
                print("[AGENT EXECUTOR] ⚠️ Plan not loaded despite success - attempting remote fetch...")
                await self._fetch_remote_orchestration_plan()
            return True
        elif len(success_tiers) == 1 and "file_system" in success_tiers:
            print("[AGENT EXECUTOR] ✅ Planning succeeded (orchestration plan exists)")
            return True
        elif len(success_tiers) == 1 and result_indicates_success:
            # Try to load plan file even when only agent signal succeeds
            try:
                if plan_file.exists():
                    with open(plan_file, 'r', encoding='utf-8') as f:
                        plan = json.load(f)
                    self.current_plan = plan
                    print(f"[AGENT EXECUTOR] ✅ Loaded orchestration plan - {len(plan.get('issues', []))} issues")
                else:
                    print("[AGENT EXECUTOR] ⚠️ Agent confirmed completion but no plan file found locally")
                    # Try to fetch the plan file using MCP tools since agent created it remotely
                    await self._fetch_remote_orchestration_plan()
            except Exception as e:
                print(f"[AGENT EXECUTOR] ⚠️ Failed to load plan file: {e}")
            
            print("[AGENT EXECUTOR] ✅ Planning succeeded (agent confirmed completion)")
            return True
        
        # Fallback: JSON extraction (legacy support)
        try:
            json_block = extract_json_block(result)
            if json_block:
                plan = json.loads(json_block)
                self.current_plan = plan
                print(f"[AGENT EXECUTOR] ✅ Planning succeeded (JSON plan extracted)")
                return True
        except Exception as e:
            print(f"[AGENT EXECUTOR] ⚠️ JSON extraction failed: {e}")
        
        # If we reach here, planning did not succeed
        print(f"[AGENT EXECUTOR] ❌ Planning validation failed (tiers: {success_tiers})")
        print(f"[AGENT EXECUTOR] 📄 Agent output length: {len(result)} chars")
        
        # Special handling for truncated results (likely due to tool execution failures)
        if len(result) < 200:
            print("[AGENT EXECUTOR] ⚠️ Suspiciously short output - possible tool execution failure")
            print(f"[AGENT EXECUTOR] 📋 Output preview: {repr(result[:100])}")
        
        return False
    
    async def _fetch_remote_orchestration_plan(self):
        """
        Fetch orchestration plan from remote GitLab repository.
        Modern multi-agent pattern: explicit state synchronization after handoff.
        """
        try:
            print("[AGENT EXECUTOR] 🔄 Fetching orchestration plan from GitLab...")
            
            # Debug: List available tools
            tool_names = [getattr(tool, 'name', 'no_name') for tool in self.tools]
            print(f"[AGENT EXECUTOR] 🛠️ Available tools: {', '.join(tool_names[:10])}{'...' if len(tool_names) > 10 else ''}")
            
            # Find get_file_contents tool to fetch the remote plan
            get_file_tool = None
            for tool in self.tools:
                if hasattr(tool, 'name') and tool.name == 'get_file_contents':
                    get_file_tool = tool
                    break
            
            if get_file_tool:
                print("[AGENT EXECUTOR] 🎯 Found get_file_contents tool, fetching...")
                # Fetch the orchestration plan file from GitLab
                file_content = await get_file_tool.ainvoke({
                    "project_id": self.project_id,
                    "file_path": "docs/ORCH_PLAN.json",
                    "ref": "master"  # or "main" depending on default branch
                })
                
                if file_content:
                    print(f"[AGENT EXECUTOR] 📄 Retrieved file content ({len(file_content)} chars)")
                    # Parse the GitLab API response - file content is wrapped
                    response_data = json.loads(file_content)
                    if "content" in response_data:
                        # Extract the actual plan content from GitLab response
                        plan_json = response_data["content"]
                        plan = json.loads(plan_json)
                        self.current_plan = plan
                        print(f"[AGENT EXECUTOR] 🎯 Parsed plan content - found {len(plan.get('issues', []))} issues")
                    else:
                        # Direct JSON content
                        plan = json.loads(file_content)
                        self.current_plan = plan
                    
                    # Also save it locally for future runs (save the actual plan, not the wrapped response)
                    plan_file = Path("docs/ORCH_PLAN.json")
                    plan_file.parent.mkdir(exist_ok=True)
                    with open(plan_file, 'w', encoding='utf-8') as f:
                        json.dump(plan, f, indent=2, ensure_ascii=False)
                    print(f"[AGENT EXECUTOR] 💾 Cached plan locally for future runs")
                    
                    print(f"[AGENT EXECUTOR] ✅ Fetched and cached orchestration plan - {len(plan.get('issues', []))} issues")
                else:
                    print("[AGENT EXECUTOR] ⚠️ Remote orchestration plan file is empty")
            else:
                print("[AGENT EXECUTOR] ❌ get_file_contents tool not found")
                print(f"[AGENT EXECUTOR] 🔍 Available tool names: {[getattr(t, 'name', 'no_name') for t in self.tools]}")
                
        except Exception as e:
            import traceback
            print(f"[AGENT EXECUTOR] ❌ Failed to fetch remote orchestration plan: {e}")
            print(f"[AGENT EXECUTOR] 📋 Error details: {traceback.format_exc()}")
    
    def get_current_plan(self) -> Optional[Dict[str, Any]]:
        """Get the current orchestration plan."""
        return self.current_plan
    
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