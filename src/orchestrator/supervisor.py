"""
Supervisor Orchestrator - Implements the Supervisor Pattern from LangGraph
Single orchestrator that coordinates all specialized agents
"""

import asyncio
from typing import Dict, Optional, Any
from pathlib import Path

from src.core.context.state import get_project_state, ProjectState
from src.core.llm.utils import extract_json_block
from src.core.context.state_tools import get_state_aware_tools
from ..infrastructure.mcp_client import get_common_tools_and_client, SafeMCPClient
from ..agents import (
    planning_agent,
    coding_agent, 
    testing_agent,
    review_agent
)


class Supervisor:
    """
    Main orchestrator using the Supervisor Pattern.
    Coordinates specialized agents and manages workflow state.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.state = get_project_state(project_id)
        self.tools = None
        self.client = None
        
        # Track agent performance
        self.agent_metrics = {
            "planning": {"calls": 0, "errors": 0},
            "coding": {"calls": 0, "errors": 0},
            "testing": {"calls": 0, "errors": 0},
            "review": {"calls": 0, "errors": 0}
        }
        
        # Pipeline failure tracking for self-healing
        self.pipeline_retry_counts = {}
        self.max_pipeline_retries = 3
    
    async def initialize(self):
        """Initialize tools and client"""
        # Get MCP tools
        mcp_tools, client = await get_common_tools_and_client()
        
        # Wrap client with SafeMCPClient for better error handling
        self.client = SafeMCPClient(client)
        
        # Add state-aware tools
        state_tools = get_state_aware_tools()
        
        # Combine MCP tools with state-aware tools
        self.tools = mcp_tools + state_tools
        
        print(f"\n[SUPERVISOR] Initialized for project {self.project_id}")
        print(f"[THREAD] {self.state.thread_id}")
        print(f"[TOOLS] {len(mcp_tools)} MCP tools + {len(state_tools)} state-aware tools")
        
        # Fetch project info to get actual default branch
        await self._fetch_project_info()
    
    async def _fetch_project_info(self):
        """Fetch project information and update state"""
        try:
            # Find get_project tool
            get_project_tool = None
            for tool in self.tools:
                if hasattr(tool, 'name') and tool.name == 'get_project':
                    get_project_tool = tool
                    break
            
            if get_project_tool:
                # Get project info
                project_info = await get_project_tool.ainvoke({"project_id": self.project_id})
                print(f"[DEBUG] Project info type: {type(project_info)}")
                print(f"[DEBUG] Project info content: {str(project_info)[:200]}...")
                
                if isinstance(project_info, dict):
                    self.state.project_info = project_info
                    # Update default branch if available
                    if 'default_branch' in project_info:
                        self.state.default_branch = project_info['default_branch']
                        print(f"[PROJECT] Default branch: {self.state.default_branch}")
                    else:
                        print(f"[PROJECT] Using default branch: {self.state.default_branch}")
                elif isinstance(project_info, str):
                    # Try to parse as JSON
                    try:
                        import json
                        parsed_info = json.loads(project_info)
                        self.state.project_info = parsed_info
                        if 'default_branch' in parsed_info:
                            self.state.default_branch = parsed_info['default_branch']
                            print(f"[PROJECT] Default branch: {self.state.default_branch}")
                        else:
                            print(f"[PROJECT] Using default branch: {self.state.default_branch}")
                    except json.JSONDecodeError:
                        print(f"[PROJECT] Could not parse project info as JSON")
                else:
                    print(f"[PROJECT] Could not parse project info - unexpected type: {type(project_info)}")
            else:
                print(f"[PROJECT] get_project tool not found, using default branch: {self.state.default_branch}")
                
        except Exception as e:
            print(f"[PROJECT] Failed to fetch project info: {e}")
            print(f"[PROJECT] Using default branch: {self.state.default_branch}")
    
    async def route_task(self, task_type: str, **kwargs) -> Any:
        """
        Route task to appropriate agent based on type.
        This is the core of the supervisor pattern.
        """
        self.agent_metrics[task_type]["calls"] += 1
        
        try:
            if task_type == "planning":
                return await self._run_planning(**kwargs)
            elif task_type == "coding":
                return await self._run_coding(**kwargs)
            elif task_type == "testing":
                return await self._run_testing(**kwargs)
            elif task_type == "review":
                return await self._run_review(**kwargs)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
                
        except Exception as e:
            self.agent_metrics[task_type]["errors"] += 1
            print(f"[ERROR] Agent {task_type} failed: {e}")
            raise
    
    async def _run_planning(self, apply: bool = False) -> bool:
        """Run planning agent and update state"""
        print("\n[SUPERVISOR] Delegating to Planning Agent...")
        
        # Set handoff context
        self.state.set_handoff(
            "supervisor",
            "planning",
            {"task": "analyze_and_plan", "apply": apply}
        )
        
        # Run planning agent with supervisor's tools
        result = await planning_agent.run(
            project_id=self.project_id,
            tools=self.tools,
            apply=apply,
            show_tokens=True
        )
        
        # Extract and cache plan
        if result:
            plan = extract_json_block(result)
            if plan:
                self.state.plan = plan
                self.state.issues = plan.get("issues", [])
                self.state.implementation_order = plan.get("implementation_order", [])
                print(f"[STATE] Cached plan with {len(self.state.issues)} issues")
                return True
        
        return False
    
    async def _run_coding(self, issue: Dict = None, branch: str = None, fix_mode: bool = False, error_context: str = "") -> bool:
        """Run coding agent for an issue or pipeline fix"""
        if fix_mode:
            print(f"\n[SUPERVISOR] Delegating Pipeline Fix to Coding Agent...")
            issues_list = [f"PIPELINE_FIX: {error_context}"]
        else:
            issue_id = issue.get("iid")
            print(f"\n[SUPERVISOR] Delegating Issue #{issue_id} to Coding Agent...")
            issues_list = [issue.get("title", "")]
            
            # Update state for regular issue
            self.state.current_issue = issue_id
            self.state.current_branch = branch
            self.state.update_issue_status(issue_id, "in_progress")
        
        # Set handoff context with cached file info
        self.state.set_handoff(
            "supervisor",
            "coding",
            {
                "issue": issue,
                "branch": branch,
                "cached_files": list(self.state.file_cache.keys()),
                "fix_mode": fix_mode,
                "error_context": error_context
            }
        )
        
        # Run coding agent with supervisor's tools
        result = await coding_agent.run(
            project_id=self.project_id,
            work_branch=branch,
            issues=issues_list,
            plan_json=self.state.plan,
            tools=self.tools,
            show_tokens=True,
            fix_mode=fix_mode,
            error_context=error_context
        )
        
        if result:
            # Check if coding agent completed successfully
            if "IMPLEMENTATION COMPLETE" in result or "implementation complete" in result.lower():
                print("[✓] Coding phase completed successfully")
                return True
            elif "error" in result.lower() or "failed" in result.lower():
                print("[!] Coding phase encountered errors")
                return False
            else:
                print("[!] Coding phase result unclear, proceeding...")
                return True
        
        return False
    
    async def _run_testing(self, issue: Dict = None, branch: str = None, fix_mode: bool = False, error_context: str = "") -> bool:
        """Run testing agent for an issue or pipeline fix"""
        if fix_mode:
            print(f"\n[SUPERVISOR] Delegating Test Fix to Testing Agent...")
        else:
            issue_id = issue.get("iid")
            print(f"\n[SUPERVISOR] Delegating tests for Issue #{issue_id} to Testing Agent...")
        
        # Set handoff from coding to testing
        self.state.set_handoff(
            "coding" if not fix_mode else "supervisor",
            "testing",
            {
                "issue": issue,
                "branch": branch,
                "implementation_complete": True
            }
        )
        
        # Run testing agent with supervisor's tools
        result = await testing_agent.run(
            project_id=self.project_id,
            work_branch=branch,
            plan_json=self.state.plan,
            tools=self.tools,
            show_tokens=True,
            fix_mode=fix_mode,
            error_context=error_context
        )
        
        return bool(result)
    
    async def _run_review(self, issue: Dict, branch: str) -> bool:
        """Run review agent to merge branch"""
        issue_id = issue.get("iid")
        print(f"\n[SUPERVISOR] Delegating merge of Issue #{issue_id} to Review Agent...")
        
        # Set handoff from testing to review
        self.state.set_handoff(
            "testing",
            "review",
            {
                "issue": issue,
                "branch": branch,
                "tests_complete": True,
                "ready_to_merge": True
            }
        )
        
        # Run review agent with supervisor's tools
        result = await review_agent.run(
            project_id=self.project_id,
            work_branch=branch,
            plan_json=self.state.plan,
            tools=self.tools,
            show_tokens=True
        )
        
        # Handle different review agent outcomes
        if isinstance(result, str):
            # Check for pipeline failure patterns
            if "PIPELINE_FAILED_" in result:
                failure_parts = result.split(": ", 1)
                failure_type = failure_parts[0]
                error_details = failure_parts[1] if len(failure_parts) > 1 else ""
                
                print(f"[SUPERVISOR] 🚨 Pipeline failure detected: {failure_type}")
                
                # Attempt self-healing
                healing_success = await self._handle_pipeline_failure(failure_type, error_details, branch)
                
                if healing_success:
                    print("[SUPERVISOR] ✅ Self-healing successful, retrying review...")
                    # Retry review after fixing
                    return await self._run_review(issue, branch)
                else:
                    print("[SUPERVISOR] ❌ Self-healing failed, escalating issue")
                    return False
                    
            elif "MERGE_COMPLETE" in result:
                # Issue was successfully completed and closed by review agent
                self.state.update_issue_status(issue_id, "complete")
                print(f"[SUPERVISOR] ✅ Issue #{issue_id} completed and closed")
                return True
                
        return False
    
    async def _handle_pipeline_failure(self, failure_type: str, error_details: str, branch: str) -> bool:
        """Handle pipeline failures with intelligent routing"""
        retry_key = f"{branch}_{failure_type}"
        retry_count = self.pipeline_retry_counts.get(retry_key, 0)
        
        if retry_count >= self.max_pipeline_retries:
            print(f"\n[SUPERVISOR] ❌ Maximum retries reached for {failure_type} on {branch}")
            return False
            
        self.pipeline_retry_counts[retry_key] = retry_count + 1
        print(f"\n[SUPERVISOR] 🔄 Handling {failure_type} (attempt {retry_count + 1}/{self.max_pipeline_retries})")
        
        # Route failure to appropriate agent
        if failure_type == "PIPELINE_FAILED_TESTS":
            print("[SUPERVISOR] → Routing to Testing Agent for test fixes")
            return await self._run_testing(branch, fix_mode=True, error_context=error_details)
            
        elif failure_type in ["PIPELINE_FAILED_BUILD", "PIPELINE_FAILED_LINT", "PIPELINE_FAILED_DEPLOY"]:
            print("[SUPERVISOR] → Routing to Coding Agent for implementation fixes")
            return await self._run_coding(branch, fix_mode=True, error_context=error_details)
            
        else:
            print(f"[SUPERVISOR] ⚠️ Unknown failure type: {failure_type}")
            return False
    
    
    async def implement_issue(self, issue: Dict) -> bool:
        """
        Complete workflow for implementing a single issue.
        Coordinates all agents in sequence.
        """
        issue_id = issue.get("iid")
        issue_title = issue.get("title", "Unknown")
        
        print("\n" + "="*60)
        print(f"[ISSUE #{issue_id}] {issue_title}")
        print("="*60)
        
        # Check if already complete
        if not self.state.should_implement_issue(issue_id):
            print(f"[SKIP] Issue #{issue_id} already complete")
            return True
        
        # Let coding agent handle branch creation from issue
        # Pass issue info and let coding agent create proper branch name
        branch = f"feature/issue-{issue_id}"  # Temporary, coding agent will create actual branch
        
        # Mark issue as in progress
        print(f"[SUPERVISOR] Setting Issue #{issue_id} to in_progress status")
        
        # Create checkpoint before starting
        checkpoint = self.state.checkpoint()
        
        try:
            # Phase 1: Coding (handles branch creation and issue status)
            print("\n[PHASE 1/3] CODING")
            if not await self.route_task("coding", issue=issue, branch=branch):
                raise Exception("Coding phase failed")
            print("[✓] Coding complete")
            
            # Brief pause
            await asyncio.sleep(1)
            
            # Phase 2: Testing
            print("\n[PHASE 2/3] TESTING")
            try:
                if not await self.route_task("testing", issue=issue, branch=branch):
                    print("[!] Testing had issues but continuing...")
                else:
                    print("[✓] Testing complete")
            except Exception as e:
                print(f"[!] Testing failed: {e} - continuing to review...")
            
            # Brief pause
            await asyncio.sleep(1)
            
            # Phase 3: Review & Merge
            print("\n[PHASE 3/3] REVIEW & MERGE")
            if not await self.route_task("review", issue=issue, branch=branch):
                raise Exception("Merge failed")
            print("[✓] Merge complete")
            
            print(f"\n[SUCCESS] Issue #{issue_id} fully implemented!")
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Failed to implement issue #{issue_id}: {e}")
            self.state.update_issue_status(issue_id, "failed")
            # Could restore from checkpoint here if needed
            return False
    
    async def run(self, mode: str = "analyze", specific_issue: Optional[str] = None):
        """
        Main orchestration entry point.
        
        Modes:
        - analyze: Just analyze and plan
        - implement: Full implementation
        - single: Implement specific issue
        """
        print("\n" + "="*60)
        print("SUPERVISOR ORCHESTRATOR")
        print("="*60)
        print(f"Project: {self.project_id}")
        print(f"Mode: {mode}")
        
        await self.initialize()
        
        # Phase 1: Planning (always run to get context)
        print("\n" + "="*60)
        print("PHASE 1: PLANNING & ANALYSIS")
        print("="*60)
        
        apply_changes = mode in ["implement", "single"]
        
        if not self.state.plan:
            # Need to run planning
            success = await self.route_task("planning", apply=apply_changes)
            if not success:
                print("[ERROR] Planning failed")
                return
        else:
            print("[CACHED] Using existing plan from state")
        
        if mode == "analyze":
            print("\n[COMPLETE] Analysis done. Run with --apply to implement.")
            await self._show_summary()
            return
        
        # Phase 2: Implementation
        print("\n" + "="*60)
        print("PHASE 2: IMPLEMENTATION")
        print("="*60)
        
        # Get issues to implement
        if specific_issue:
            # Single issue mode
            issues_to_implement = [
                i for i in self.state.issues 
                if str(i.get("iid")) == str(specific_issue)
            ]
            if not issues_to_implement:
                print(f"[ERROR] Issue {specific_issue} not found")
                return
        else:
            # All issues mode
            issues_dict = {str(i["iid"]): i for i in self.state.issues}
            issues_to_implement = []
            for iid in self.state.implementation_order:
                if iid in issues_dict:
                    issues_to_implement.append(issues_dict[iid])
        
        print(f"[PLAN] Will implement {len(issues_to_implement)} issues")
        
        # Implement each issue
        for idx, issue in enumerate(issues_to_implement, 1):
            print(f"\n[PROGRESS] {idx}/{len(issues_to_implement)}")
            
            success = await self.implement_issue(issue)
            
            if not success:
                print(f"[WARNING] Issue #{issue['iid']} failed, continuing...")
            
            # Checkpoint after each issue
            self.state.checkpoint()
            
            # Brief pause between issues
            if idx < len(issues_to_implement):
                print("\n[PAUSE] 2 seconds...")
                await asyncio.sleep(2)
        
        # Phase 3: Summary
        await self._show_summary()
        
        # Save final state
        state_file = self.state.save_to_file()
        print(f"\n[STATE] Saved to {state_file}")
        
        # Clean up MCP client at the end
        await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources managed by the supervisor."""
        if self.client:
            # SafeMCPClient handles all error suppression internally
            await self.client.close()
            # The SafeMCPClient will print the clean close message
    
    async def _show_summary(self):
        """Show execution summary"""
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        summary = self.state.get_summary()
        print(f"Project: {summary['project_id']}")
        print(f"Thread: {summary['thread_id']}")
        print(f"Issues: {summary['completed_issues']}/{summary['total_issues']} complete")
        print(f"Cached Files: {summary['cached_files']}")
        print(f"Checkpoints: {summary['checkpoints']}")
        
        # Show file status
        file_status = summary['file_status']
        print(f"File Status: Empty={file_status['empty']}, "
              f"Partial={file_status['partial']}, "
              f"Complete={file_status['complete']}")
        
        # Show agent metrics
        print("\nAgent Metrics:")
        for agent, metrics in self.agent_metrics.items():
            if metrics["calls"] > 0:
                error_rate = (metrics["errors"] / metrics["calls"]) * 100
                print(f"  {agent}: {metrics['calls']} calls, "
                      f"{metrics['errors']} errors ({error_rate:.1f}%)")
        
        print("\n[COMPLETE] Orchestration finished")


async def run_supervisor(
    project_id: str,
    mode: str = "analyze",
    specific_issue: Optional[str] = None,
    resume_from: Optional[Path] = None,
    tech_stack: Optional[Dict[str, str]] = None
):
    """
    Main entry point for supervisor orchestrator.
    
    Args:
        project_id: GitLab project ID
        mode: "analyze" (plan only) or "implement" (full) or "single" (one issue)
        specific_issue: Issue ID for single mode
        resume_from: Path to state file to resume from
        tech_stack: Technology stack preferences for new projects
    """
    supervisor = Supervisor(project_id)
    
    # Store tech stack preferences in supervisor state
    if tech_stack:
        supervisor.state.tech_stack = tech_stack
        print(f"[TECH STACK] Using specified: {tech_stack}")
    
    # Resume from checkpoint if provided
    if resume_from and resume_from.exists():
        print(f"[RESUME] Loading state from {resume_from}")
        supervisor.state = ProjectState.load_from_file(resume_from)
    
    await supervisor.run(mode, specific_issue)