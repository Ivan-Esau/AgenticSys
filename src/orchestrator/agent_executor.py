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
    
    def __init__(self, project_id: str, state_manager: Any, tools: List[Any]):
        self.project_id = project_id
        # state_manager removed (was broken state system)
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
        
        # Load orchestration plan if detected as successful
        if success:
            plan_file = Path("docs/ORCH_PLAN.json")
            try:
                if plan_file.exists():
                    with open(plan_file, 'r', encoding='utf-8') as f:
                        plan = json.load(f)
                    self.current_plan = plan
                    
                    # Convert plan format if needed (handle both old and new formats)
                    self._normalize_plan_format()
                    
                    issue_count = len(self.current_plan.get('issues', []))
                    print(f"[AGENT EXECUTOR] ✅ Loaded orchestration plan - {issue_count} issues")
                else:
                    print("[AGENT EXECUTOR] ⚠️ Success detected but no local plan file - fetching remote...")
                    await self._fetch_remote_orchestration_plan()
            except Exception as e:
                print(f"[AGENT EXECUTOR] ⚠️ Error loading plan file: {e}")
                await self._fetch_remote_orchestration_plan()
            
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
                    
                    # Normalize the plan format
                    self._normalize_plan_format()
                    
                    # Also save it locally for future runs (save the actual plan, not the wrapped response)
                    plan_file = Path("docs/ORCH_PLAN.json")
                    plan_file.parent.mkdir(exist_ok=True)
                    with open(plan_file, 'w', encoding='utf-8') as f:
                        json.dump(self.current_plan, f, indent=2, ensure_ascii=False)
                    print(f"[AGENT EXECUTOR] 💾 Cached plan locally for future runs")
                    
                    print(f"[AGENT EXECUTOR] ✅ Fetched and cached orchestration plan - {len(self.current_plan.get('issues', []))} issues")
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
        
    def _normalize_plan_format(self):
        """
        Normalize the orchestration plan format to ensure it has an 'issues' array.
        Converts from the metadata format to the expected format with actual issues.
        """
        if not self.current_plan:
            return
        
        # If plan already has issues array, nothing to do
        if 'issues' in self.current_plan and isinstance(self.current_plan['issues'], list):
            return
        
        # Convert from metadata format to issues array format
        issues = []
        
        # Extract issues from implementation_status section
        if 'implementation_status' in self.current_plan:
            for key, value in self.current_plan['implementation_status'].items():
                # Extract issue ID from key (e.g., "issue_1" -> 1)
                issue_id = key.replace('issue_', '')
                
                issue = {
                    'iid': issue_id,
                    'title': value.get('description', f'Issue {issue_id}'),
                    'description': value.get('description', ''),
                    'implementation_status': value.get('status', 'not_started'),
                    'files': value.get('files', []),
                    'acceptance_criteria': value.get('acceptance_criteria', [])
                }
                
                # Add dependency information if available
                if 'issue_dependencies' in self.current_plan:
                    for dep in self.current_plan['issue_dependencies']:
                        if str(dep.get('issue_id')) == str(issue_id):
                            issue['depends_on'] = dep.get('depends_on', [])
                            issue['required_for'] = dep.get('required_for', [])
                            break
                
                issues.append(issue)
        
        # If no issues found in implementation_status, try development_phases
        if not issues and 'development_phases' in self.current_plan:
            for phase in self.current_plan['development_phases']:
                issue = {
                    'iid': str(phase.get('issue', phase.get('phase', 0))),
                    'title': phase.get('description', f"Phase {phase.get('phase', 0)}"),
                    'description': phase.get('description', ''),
                    'priority': phase.get('priority', 'medium'),
                    'implementation_status': 'not_started'
                }
                issues.append(issue)
        
        # Sort issues by ID
        issues.sort(key=lambda x: int(x['iid']) if x['iid'].isdigit() else 0)
        
        # Update the plan with normalized issues array
        self.current_plan['issues'] = issues
        
        print(f"[AGENT EXECUTOR] 📋 Normalized plan format - extracted {len(issues)} issues from metadata")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return {
            "project_id": self.project_id,
            "current_executions": len(self.current_executions),
            "completed_executions": len(self.execution_history),
            "has_plan": self.current_plan is not None,
            "planned_issues": len(self.current_plan.get("issues", [])) if self.current_plan else 0
        }