"""
Supervisor Orchestrator - Clean modular design
Main orchestrator that coordinates specialized modules for workflow management.
"""

import asyncio
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime

from src.core.context.state import get_project_state, ProjectState
from src.core.context.state_tools import get_state_aware_tools
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
    Coordinates specialized modules for clean separation of concerns.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.state = get_project_state(project_id)
        self.tools = None
        self.client = None
        
        # Initialize modular components
        self.router = AgentRouter()
        self.executor = AgentExecutor(project_id, self.state, [])
        self.performance_tracker = PerformanceTracker()
        self.summary_reporter = SummaryReporter(project_id, self.state.thread_id)
        self.pipeline_manager = PipelineManager()
        self.issue_manager = IssueManager(project_id, self.state)
    
    async def initialize(self):
        """Initialize tools, client, and all modular components"""
        # Get MCP tools
        mcp_tools, client = await get_common_tools_and_client()
        
        # Wrap client with SafeMCPClient for better error handling
        self.client = SafeMCPClient(client)
        
        # Add state-aware tools
        state_tools = get_state_aware_tools()
        
        # Combine MCP tools with state-aware tools
        self.tools = mcp_tools + state_tools
        
        # Update executor with tools
        self.executor.tools = self.tools
        
        print(f"\n[SUPERVISOR] Initialized for project {self.project_id}")
        print(f"[THREAD] {self.state.thread_id}")
        print(f"[TOOLS] {len(mcp_tools)} MCP tools + {len(state_tools)} state-aware tools")
        print(f"[MODULES] Router, Executor, Performance, Summary, Pipeline, Issue managers loaded")
        
        # Set execution mode for reporting
        self.summary_reporter.set_execution_mode("supervisor_orchestration")
        
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
                    except json.JSONDecodeError:
                        print(f"[PROJECT] Could not parse project info as JSON")
            else:
                print(f"[PROJECT] get_project tool not found, using default branch: {self.state.default_branch}")
                
        except Exception as e:
            print(f"[PROJECT] Failed to fetch project info: {e}")
            print(f"[PROJECT] Using default branch: {self.state.default_branch}")
    
    async def route_task(self, task_type: str, **kwargs) -> Any:
        """
        Route task to appropriate agent using modular routing system.
        """
        # Use router to validate and get routing decision
        routing_result = self.router.route_task(task_type, **kwargs)
        
        if not routing_result["success"]:
            raise ValueError(routing_result["error"])
        
        # Start performance tracking
        timing_id = self.performance_tracker.start_task_timing(routing_result["agent"], task_type)
        
        try:
            print(f"\n[SUPERVISOR] 🎯 Routing {task_type.upper()} task to {routing_result['agent']} agent...")
            
            # Route to appropriate executor method
            result = None
            if task_type == "planning":
                result = await self.executor.execute_planning_agent(**kwargs)
            elif task_type == "coding":
                result = await self.executor.execute_coding_agent(**kwargs)
            elif task_type == "testing":
                result = await self.executor.execute_testing_agent(**kwargs)
            elif task_type == "review":
                result = await self.executor.execute_review_agent(**kwargs)
            
            # End performance tracking
            self.performance_tracker.end_task_timing(timing_id, success=bool(result))
            
            # Mark task completion in router
            self.router.complete_task(routing_result["agent"], success=bool(result))
            
            return result
                
        except Exception as e:
            # End performance tracking with error
            self.performance_tracker.end_task_timing(timing_id, success=False, error=str(e))
            
            # Mark task completion as failed
            self.router.complete_task(routing_result["agent"], success=False)
            
            # Record error for reporting
            self.summary_reporter.record_error(str(e), routing_result["agent"])
            
            print(f"[ERROR] ❌ Agent {task_type} failed: {e}")
            
            # Attempt recovery
            recovery_result = await self._attempt_recovery(task_type, e, **kwargs)
            if recovery_result:
                print(f"[SUPERVISOR] ✅ Recovery successful for {task_type}")
                return recovery_result
            
            raise Exception(f"Task {task_type} failed and recovery unsuccessful: {e}")
    
    async def implement_issue(self, issue: Dict) -> bool:
        """
        Implement a single issue using the modular issue manager.
        """
        issue_id = issue.get("iid")
        
        # Validate issue structure using validator
        if not IssueValidator.validate_issue_structure(issue):
            self.summary_reporter.record_error(f"Invalid issue structure for #{issue_id}", "validation")
            return False
        
        # Validate dependencies
        if not IssueValidator.validate_issue_dependencies(
            issue, 
            self.state.plan, 
            self.state.implementation_status
        ):
            self.summary_reporter.record_error(f"Dependencies not met for issue #{issue_id}", "validation")
            return False
        
        # Record issue processing start
        self.summary_reporter.record_issue_processed(issue, "started")
        
        # Delegate to issue manager for full workflow
        result = await self.issue_manager.implement_issue(issue, self.executor)
        
        # Record final status
        final_status = "complete" if result else "failed"
        self.summary_reporter.record_issue_processed(issue, final_status)
        
        return result
    
    async def _handle_pipeline_failure(self, failure_result: str, branch: str) -> bool:
        """
        Handle pipeline failures using the pipeline manager.
        """
        return await self.pipeline_manager.handle_pipeline_failure(
            failure_result, branch, self.executor
        )
    
    async def _attempt_recovery(self, task_type: str, error: Exception, **kwargs) -> Any:
        """Attempt recovery from task failures using simple strategies."""
        error_str = str(error).lower()
        
        try:
            # Network/connection errors
            if "network" in error_str or "connection" in error_str or "timeout" in error_str:
                print(f"[SUPERVISOR] 🔄 Attempting recovery for network error...")
                await asyncio.sleep(5)  # Wait and retry
                return None  # Return None to trigger retry
            
            # Model/LLM errors
            elif "unsupported provider" in error_str or "model" in error_str:
                print(f"[SUPERVISOR] 🔄 Attempting recovery for model error...")
                return None
                
            # GitLab API errors
            elif "404" in error_str or "gitlab" in error_str:
                print(f"[SUPERVISOR] 🔄 Attempting recovery for GitLab API error...")
                await asyncio.sleep(3)
                return None
                
            else:
                print(f"[SUPERVISOR] ❌ No recovery strategy for: {error_str[:100]}")
                return None
                
        except Exception as recovery_error:
            print(f"[SUPERVISOR] ❌ Recovery attempt failed: {recovery_error}")
            return None
    
    async def run(self, mode: str = "analyze", specific_issue: Optional[str] = None):
        """
        Main orchestration entry point using modular components.
        
        Modes:
        - analyze: Just analyze and plan
        - implement: Full implementation
        - single: Implement specific issue
        """
        # Validate mode
        valid_modes = {"analyze", "implement", "single", "resume"}
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Valid modes: {valid_modes}")
        
        print("\n" + "="*60)
        print("SUPERVISOR ORCHESTRATOR (MODULAR)")
        print("="*60)
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
        
        if not self.state.plan:
            # Need to run planning
            success = await self.route_task("planning", apply=apply_changes)
            if not success:
                print("[ERROR] Planning failed")
                self.summary_reporter.record_error("Planning phase failed", "planning")
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
        
        # Implement each issue using issue manager
        for idx, issue in enumerate(issues_to_implement, 1):
            print(f"\n[PROGRESS] {idx}/{len(issues_to_implement)}")
            
            # Use modular issue implementation
            success = await self.implement_issue(issue)
            
            if not success:
                print(f"[WARNING] ❌ Issue #{issue['iid']} failed")
            else:
                print(f"[SUCCESS] ✅ Issue #{issue['iid']} completed successfully")
            
            # Checkpoint after each issue
            try:
                self.state.checkpoint()
                self.summary_reporter.increment_checkpoints()
            except Exception as e:
                print(f"[WARNING] Checkpoint failed: {e}")
            
            # Brief pause between issues
            if idx < len(issues_to_implement):
                print("\n[PAUSE] 3 seconds between issues...")
                await asyncio.sleep(3)
        
        # Phase 3: Summary
        await self._show_summary()
        
        # Save final state
        state_file = self.state.save_to_file()
        print(f"\n[STATE] Saved to {state_file}")
        
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
        print("EXECUTION SUMMARY (MODULAR)")
        print("="*60)
        
        # Get metrics from various components
        state_info = self.state.get_summary()
        agent_metrics = self.performance_tracker.get_agent_metrics()
        router_stats = self.router.get_routing_statistics()
        pipeline_stats = self.pipeline_manager.get_failure_statistics()
        issue_stats = self.issue_manager.get_issue_statistics()
        
        # Use summary reporter for console output
        self.summary_reporter.print_console_summary(
            state_info=state_info,
            agent_metrics=agent_metrics,
            include_details=True
        )
        
        # Show additional modular component stats
        print("\n" + "="*40)
        print("MODULE STATISTICS")
        print("="*40)
        
        print(f"Router Efficiency: {router_stats.get('routing_efficiency', 0):.2f}")
        print(f"Pipeline Recovery Rate: {pipeline_stats.get('recovery_rate', 0):.2f}")
        print(f"Issue Success Rate: {issue_stats.get('success_rate', 0):.2f}")
        
        # Show recommendations
        if router_stats.get('recommendations'):
            print("\nRecommendations:")
            for rec in router_stats['recommendations'][:3]:
                print(f"  • {rec}")
        
        print("\n[COMPLETE] Modular orchestration finished")


# Main entry function using the clean modular supervisor
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