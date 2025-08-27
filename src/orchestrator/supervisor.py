"""
Supervisor Orchestrator - Implements the Supervisor Pattern from LangGraph
Single orchestrator that coordinates all specialized agents
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from ..core.state import get_project_state, ProjectState
from ..core.utils import extract_json_block
from ..infrastructure.mcp_client import get_common_tools_and_client
from ..agents import (
    planning_agent,
    coding_agent, 
    testing_agent,
    review_agent,
    pipeline_agent
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
            "review": {"calls": 0, "errors": 0},
            "pipeline": {"calls": 0, "errors": 0}
        }
    
    async def initialize(self):
        """Initialize tools and client"""
        self.tools, self.client = await get_common_tools_and_client()
        print(f"\n[SUPERVISOR] Initialized for project {self.project_id}")
        print(f"[THREAD] {self.state.thread_id}")
    
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
            elif task_type == "pipeline":
                return await self._run_pipeline(**kwargs)
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
    
    async def _run_coding(self, issue: Dict, branch: str) -> bool:
        """Run coding agent for an issue"""
        issue_id = issue.get("iid")
        print(f"\n[SUPERVISOR] Delegating Issue #{issue_id} to Coding Agent...")
        
        # Set handoff context with cached file info
        self.state.set_handoff(
            "supervisor",
            "coding",
            {
                "issue": issue,
                "branch": branch,
                "cached_files": list(self.state.file_cache.keys())
            }
        )
        
        # Update state
        self.state.current_issue = issue_id
        self.state.current_branch = branch
        self.state.update_issue_status(issue_id, "in_progress")
        
        # Run coding agent with supervisor's tools
        result = await coding_agent.run(
            project_id=self.project_id,
            work_branch=branch,
            issues=[f"#{issue_id} | {issue.get('title')}"],
            plan_json=self.state.plan,
            tools=self.tools,
            show_tokens=True
        )
        
        if result:
            # Cache any files mentioned in the result
            # This is where we could parse the result to update file cache
            return True
        
        return False
    
    async def _run_testing(self, issue: Dict, branch: str) -> bool:
        """Run testing agent for an issue"""
        issue_id = issue.get("iid")
        print(f"\n[SUPERVISOR] Delegating tests for Issue #{issue_id} to Testing Agent...")
        
        # Set handoff from coding to testing
        self.state.set_handoff(
            "coding",
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
            branch=branch,
            plan_json=self.state.plan,
            tools=self.tools,
            show_tokens=True
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
            branch=branch,
            plan_json=self.state.plan,
            tools=self.tools,
            show_tokens=True
        )
        
        if result:
            self.state.update_issue_status(issue_id, "complete")
            return True
        
        return False
    
    async def _run_pipeline(self, branch: str, mr_iid: Optional[str] = None) -> bool:
        """Run pipeline agent to check CI/CD"""
        print(f"\n[SUPERVISOR] Delegating pipeline check to Pipeline Agent...")
        
        # Run pipeline agent with supervisor's tools
        result = await pipeline_agent.run(
            project_id=self.project_id,
            ref=branch,
            mr_iid=mr_iid,
            tools=self.tools,
            show_tokens=False
        )
        
        return bool(result)
    
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
        
        # Create unique branch
        branch = f"issue-{issue_id}-{datetime.now().strftime('%H%M%S')}"
        print(f"[BRANCH] {branch}")
        
        # Create checkpoint before starting
        checkpoint = self.state.checkpoint()
        
        try:
            # Phase 1: Coding
            print("\n[PHASE 1/3] CODING")
            if not await self.route_task("coding", issue=issue, branch=branch):
                raise Exception("Coding phase failed")
            print("[✓] Coding complete")
            
            # Brief pause
            await asyncio.sleep(1)
            
            # Phase 2: Testing
            print("\n[PHASE 2/3] TESTING")
            if not await self.route_task("testing", issue=issue, branch=branch):
                print("[!] Testing had issues but continuing...")
            else:
                print("[✓] Testing complete")
            
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
            try:
                # Only try to close if the client has a close method
                if hasattr(self.client, 'close'):
                    await self.client.close()
                    print(f"\n[SUPERVISOR] MCP client closed")
            except Exception as e:
                # MCP close may fail with 404 - this is expected and harmless
                if "Session termination failed" not in str(e):
                    print(f"\n[SUPERVISOR] Client cleanup note: {e}")
                pass
    
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
    resume_from: Optional[Path] = None
):
    """
    Main entry point for supervisor orchestrator.
    
    Args:
        project_id: GitLab project ID
        mode: "analyze" (plan only) or "implement" (full) or "single" (one issue)
        specific_issue: Issue ID for single mode
        resume_from: Path to state file to resume from
    """
    supervisor = Supervisor(project_id)
    
    # Resume from checkpoint if provided
    if resume_from and resume_from.exists():
        print(f"[RESUME] Loading state from {resume_from}")
        supervisor.state = ProjectState.load_from_file(resume_from)
    
    await supervisor.run(mode, specific_issue)