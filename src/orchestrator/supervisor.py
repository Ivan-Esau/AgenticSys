"""
Supervisor Orchestrator - Clean modular design without broken state system
Main orchestrator that coordinates specialized modules for workflow management.
"""

import asyncio
import json
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime

from ..infrastructure.mcp_client import get_common_tools_and_client, SafeMCPClient

# Import modular components
from .validation.task_validator import TaskValidator
from .validation.issue_validator import IssueValidator
from .validation.plan_validator import PlanValidator
from .metrics.performance_tracker import PerformanceTracker
from .metrics.summary_reporter import SummaryReporter
from .workflow.pipeline_manager import PipelineManager
from .workflow.issue_manager import IssueManager
from .agent_router import AgentRouter
from .agent_executor import AgentExecutor


class Supervisor:
    """
    Main orchestrator using modular components.
    Simplified version without broken state management.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.tools = None
        self.client = None
        self.default_branch = "master"
        self.current_plan = None
        
        # Initialize modular components
        self.router = AgentRouter()
        self.executor = AgentExecutor(project_id, None, [])
        self.performance_tracker = PerformanceTracker()
        self.summary_reporter = SummaryReporter(project_id, f"thread_{project_id}")
        self.pipeline_manager = PipelineManager()
        self.issue_manager = IssueManager(project_id, None)
    
    async def initialize(self):
        """Initialize tools, client, and all modular components"""
        try:
            # Get MCP tools
            mcp_tools, client = await get_common_tools_and_client()
            
            # Wrap client with SafeMCPClient for better error handling
            self.client = SafeMCPClient(client)
            
            # Use only MCP tools (removed broken state tools)
            self.tools = mcp_tools
            
            # Update executor with tools
            self.executor.tools = self.tools
            
            print(f"\n[SUPERVISOR] Initialized for project {self.project_id}")
            print(f"[TOOLS] {len(mcp_tools)} MCP tools (state tools removed)")
            print(f"[MODULES] Router, Executor, Performance, Summary, Pipeline, Issue managers loaded")
            
            # Set execution mode for reporting
            self.summary_reporter.set_execution_mode("supervisor_orchestration")
            
            # Fetch project info to get actual default branch
            await self._fetch_project_info()
            
        except Exception as e:
            print(f"[SUPERVISOR] ❌ Initialization failed: {e}")
            raise
    
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
                
                if isinstance(project_info, dict):
                    # Update default branch if available
                    if 'default_branch' in project_info:
                        self.default_branch = project_info['default_branch']
                        print(f"[PROJECT] Default branch: {self.default_branch}")
                    else:
                        print(f"[PROJECT] Using default branch: {self.default_branch}")
                elif isinstance(project_info, str):
                    # Try to parse as JSON
                    try:
                        parsed_info = json.loads(project_info)
                        if 'default_branch' in parsed_info:
                            self.default_branch = parsed_info['default_branch']
                            print(f"[PROJECT] Default branch: {self.default_branch}")
                    except json.JSONDecodeError:
                        print(f"[PROJECT] Could not parse project info as JSON")
            else:
                print(f"[PROJECT] get_project tool not found, using default branch: {self.default_branch}")
                
        except Exception as e:
            print(f"[PROJECT] Failed to fetch project info: {e}")
            print(f"[PROJECT] Using default branch: {self.default_branch}")
    
    async def route_task(self, task_type: str, **kwargs) -> Any:
        """
        Modern multi-agent task routing with proper handoff mechanisms.
        Implements 2024-2025 multi-agent orchestration patterns.
        """
        # Use router to validate and get routing decision
        routing_result = self.router.route_task(task_type, **kwargs)
        
        if not routing_result["success"]:
            raise ValueError(routing_result["error"])
        
        # Start performance tracking
        timing_id = self.performance_tracker.start_task_timing(routing_result["agent"], task_type)
        
        try:
            print(f"\n[SUPERVISOR] 🎯 Delegating {task_type.upper()} task to {routing_result['agent']} agent...")
            print(f"[SUPERVISOR] 🤝 Agent handoff initiated...")
            
            # Route to appropriate executor method with enhanced monitoring
            result = None
            if task_type == "planning":
                result = await self.executor.execute_planning_agent(**kwargs)
                if result:
                    # Get the current plan from executor using modern coordination
                    self.current_plan = self.executor.get_current_plan()
                    print(f"[SUPERVISOR] ✅ Planning agent handoff complete - plan acquired")
                else:
                    print(f"[SUPERVISOR] ❌ Planning agent handoff failed")
                    
            elif task_type == "coding":
                result = await self.executor.execute_coding_agent(**kwargs)
                if result:
                    print(f"[SUPERVISOR] ✅ Coding agent handoff complete")
                else:
                    print(f"[SUPERVISOR] ❌ Coding agent handoff failed")
                    
            elif task_type == "testing":
                result = await self.executor.execute_testing_agent(**kwargs)
                if result:
                    print(f"[SUPERVISOR] ✅ Testing agent handoff complete")
                else:
                    print(f"[SUPERVISOR] ❌ Testing agent handoff failed")
                    
            elif task_type == "review":
                result = await self.executor.execute_review_agent(**kwargs)
                if result:
                    print(f"[SUPERVISOR] ✅ Review agent handoff complete")
                else:
                    print(f"[SUPERVISOR] ❌ Review agent handoff failed")
            
            # End performance tracking
            self.performance_tracker.end_task_timing(timing_id, success=bool(result))
            
            # Mark task completion in router
            self.router.complete_task(routing_result["agent"], success=bool(result))
            
            if result:
                print(f"[SUPERVISOR] 🎉 {task_type.upper()} task completed successfully")
            else:
                print(f"[SUPERVISOR] ⚠️ {task_type.upper()} task completed with issues")
            
            return result
                
        except Exception as e:
            # End performance tracking with error
            self.performance_tracker.end_task_timing(timing_id, success=False, error=str(e))
            
            # Mark task completion as failed
            self.router.complete_task(routing_result["agent"], success=False)
            
            # Record error for reporting
            self.summary_reporter.record_error(str(e), routing_result["agent"])
            
            print(f"[SUPERVISOR] ❌ Agent coordination failed: {e}")
            raise Exception(f"Task {task_type} failed: {e}")
    
    async def implement_issue(self, issue: Dict) -> bool:
        """
        Implement a single issue using the modular issue manager.
        """
        issue_id = issue.get("iid")
        
        # Validate issue structure using validator
        if not IssueValidator.validate_issue_structure(issue):
            self.summary_reporter.record_error(f"Invalid issue structure for #{issue_id}", "validation")
            return False
        
        # Record issue processing start
        self.summary_reporter.record_issue_processed(issue, "started")
        
        # Delegate to issue manager for full workflow
        result = await self.issue_manager.implement_issue(issue, self.executor)
        
        # Record final status
        final_status = "complete" if result else "failed"
        self.summary_reporter.record_issue_processed(issue, final_status)
        
        # Update orchestration plan if issue was completed successfully
        if result:
            await self._update_orchestration_plan_for_completed_issue(issue_id)
        
        return result
    
    async def execute(self, mode: str = "implement", specific_issue: str = None):
        """
        Main execution method for supervisor orchestration.
        Simplified without broken state management.
        """
        print(f"[SUPERVISOR] 🚀 Starting execution")
        print(f"Project: {self.project_id}")
        print(f"Mode: {mode}")
        
        # Initialize with validation
        try:
            await self.initialize()
        except Exception as e:
            print(f"[SUPERVISOR] ❌ Initialization failed: {e}")
            self.summary_reporter.record_error(str(e), "initialization")
            return
        
        # Phase 1: Planning (always run to get context)
        print("\n" + "="*60)
        print("PHASE 1: PLANNING & ANALYSIS")
        print("="*60)
        
        apply_changes = mode in ["implement", "single"]
        
        if not self.current_plan:
            # Need to run planning
            success = await self.route_task("planning", apply=apply_changes)
            if not success:
                print("[ERROR] Planning failed")
                self.summary_reporter.record_error("Planning phase failed", "planning")
                return
        else:
            print("[CACHED] Using existing plan")
        
        if mode == "analyze":
            print("\n[COMPLETE] Analysis done. Run with --apply to implement.")
            await self._show_summary()
            return
        
        # Phase 2: Implementation
        if self.current_plan and self.current_plan.get("issues"):
            print("\n" + "="*60)
            print("PHASE 2: IMPLEMENTATION")
            print("="*60)
            
            issues = self.current_plan.get("issues", [])
            
            # Get issues to implement
            if specific_issue:
                # Single issue mode
                issues_to_implement = [
                    i for i in issues 
                    if str(i.get("iid")) == str(specific_issue)
                ]
                if not issues_to_implement:
                    print(f"[ERROR] Issue {specific_issue} not found")
                    return
            else:
                # All issues mode
                issues_to_implement = issues
            
            print(f"[PLAN] Will implement {len(issues_to_implement)} issues")
            
            # Implement each issue using issue manager
            for idx, issue in enumerate(issues_to_implement, 1):
                print(f"\n[PROGRESS] {idx}/{len(issues_to_implement)}")
                
                # Use modular issue implementation
                success = await self.implement_issue(issue)
                
                if not success:
                    print(f"[WARNING] ❌ Issue #{issue['iid']} failed")
                else:
                    print(f"[SUCCESS] ✅ Issue #{issue['iid']} completed successfully")
                
                # Brief pause between issues
                if idx < len(issues_to_implement):
                    print("\n[PAUSE] 3 seconds between issues...")
                    await asyncio.sleep(3)
        
        # Phase 3: Summary
        await self._show_summary()
        
        # Clean up MCP client
        await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources managed by the supervisor."""
        self.summary_reporter.finalize_execution()
        
        if self.client:
            await self.client.close()
    
    async def _show_summary(self):
        """Show execution summary using summary reporter"""
        print("\n" + "="*60)
        print("EXECUTION SUMMARY")
        print("="*60)
        
        # Generate and display summary report
        summary = self.summary_reporter.generate_summary()
        print(summary)
        
        # Show performance metrics
        perf_summary = self.performance_tracker.get_performance_summary()
        print(f"\n[PERFORMANCE] {perf_summary}")
        
        # Show execution statistics
        exec_summary = self.executor.get_execution_summary()
        print(f"[EXECUTION] {exec_summary}")
    
    async def _attempt_recovery(self, task_type: str, error: Exception, **kwargs) -> Optional[Any]:
        """
        Attempt recovery from task failures.
        Simplified version without complex state management.
        """
        print(f"[RECOVERY] Attempting recovery for {task_type} failure...")
        
        # Simple retry logic - could be expanded
        try:
            # Wait a bit before retry
            await asyncio.sleep(2)
            
            # Try once more
            if task_type == "planning":
                return await self.executor.execute_planning_agent(**kwargs)
            elif task_type == "coding":
                return await self.executor.execute_coding_agent(**kwargs)
            elif task_type == "testing":
                return await self.executor.execute_testing_agent(**kwargs)
            elif task_type == "review":
                return await self.executor.execute_review_agent(**kwargs)
                
        except Exception as recovery_error:
            print(f"[RECOVERY] Recovery failed: {recovery_error}")
            
        return None
    
    async def _update_orchestration_plan_for_completed_issue(self, issue_id: str):
        """
        Update the orchestration plan to mark an issue as completed.
        This addresses the user's request to update the plan when issues are implemented.
        """
        try:
            # Check if we have a current plan to update
            if not self.current_plan:
                print(f"[PLAN UPDATE] No current plan to update for issue #{issue_id}")
                return
            
            # Find and update the issue in the current plan
            updated = False
            if "issues" in self.current_plan:
                for issue in self.current_plan["issues"]:
                    if str(issue.get("iid")) == str(issue_id):
                        issue["implementation_status"] = "complete"
                        issue["completed_at"] = datetime.now().isoformat()
                        updated = True
                        break
            
            if updated:
                # Update overall plan statistics
                if "completed_issues" in self.current_plan:
                    self.current_plan["completed_issues"] += 1
                else:
                    self.current_plan["completed_issues"] = 1
                
                # Update implementation status if all issues are complete
                total_issues = len(self.current_plan.get("issues", []))
                completed_issues = self.current_plan.get("completed_issues", 0)
                
                if completed_issues >= total_issues:
                    self.current_plan["implementation_status"] = "complete"
                elif completed_issues > 0:
                    self.current_plan["implementation_status"] = "partial"
                
                # Write updated plan back to file
                plan_file = Path("docs/ORCH_PLAN.json")
                if plan_file.exists() or plan_file.parent.exists():
                    plan_file.parent.mkdir(exist_ok=True)
                    with open(plan_file, 'w', encoding='utf-8') as f:
                        json.dump(self.current_plan, f, indent=2, ensure_ascii=False)
                    
                    print(f"[PLAN UPDATE] ✅ Updated orchestration plan - Issue #{issue_id} marked as complete")
                    print(f"[PLAN UPDATE] Progress: {completed_issues}/{total_issues} issues complete")
                else:
                    print(f"[PLAN UPDATE] ⚠️ Could not write to docs/ORCH_PLAN.json - directory may not exist")
            else:
                print(f"[PLAN UPDATE] ⚠️ Issue #{issue_id} not found in current plan")
                
        except Exception as e:
            print(f"[PLAN UPDATE] ❌ Failed to update orchestration plan for issue #{issue_id}: {e}")
            self.summary_reporter.record_error(f"Plan update failed for issue #{issue_id}: {e}", "plan_update")


# Helper function for running supervisor (expected by __init__.py)
async def run_supervisor(
    project_id: str, 
    mode: str = "implement", 
    specific_issue: str = None, 
    resume_from: str = None, 
    tech_stack: dict = None
):
    """
    Helper function to run supervisor with the specified parameters.
    
    Args:
        project_id: GitLab project ID
        mode: Execution mode ("analyze" or "implement")
        specific_issue: Specific issue ID for single issue mode
        resume_from: Path to resume state (not used in simplified version)
        tech_stack: Technology stack preferences (not used in simplified version)
    """
    supervisor = Supervisor(project_id)
    
    # Map mode to supervisor execution mode
    exec_mode = "implement" if mode == "implement" else "analyze"
    
    await supervisor.execute(mode=exec_mode, specific_issue=specific_issue)