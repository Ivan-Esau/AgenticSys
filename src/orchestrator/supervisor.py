"""
Supervisor Orchestrator - Refactored Version
Main orchestrator that coordinates specialized modules for workflow management.
"""

import asyncio
from typing import Dict, Optional, Any, List
from enum import Enum
from datetime import datetime

from ..infrastructure.mcp_client import get_common_tools_and_client, SafeMCPClient

# Import core components
from .core import PerformanceTracker, Router, AgentExecutor

# Import manager components
from .managers import IssueManager, PlanningManager
from .managers.tech_stack_detector import TechStackDetector

# Import utility helpers
from .utils.issue_helpers import get_issue_iid

# Import integration components
from .integrations import MCPIntegration

# Import analytics components
from .analytics import RunLogger, IssueTracker
from .analytics.csv_exporter import CSVExporter
from pathlib import Path


class ExecutionState(Enum):
    """Execution state for better flow control"""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    PREPARING = "preparing"
    IMPLEMENTING = "implementing"
    COMPLETING = "completing"
    FAILED = "failed"
    COMPLETED = "completed"




class Supervisor:
    """
    Refactored orchestrator using modular components for better maintainability.
    """

    def __init__(self, project_id: str, tech_stack: dict = None, llm_config: Dict[str, Any] = None, mcp_log_callback=None):
        self.project_id = project_id
        self.state = ExecutionState.INITIALIZING
        self.provided_tech_stack = tech_stack
        self.min_coverage = 70.0

        # Callbacks for Web GUI integration
        self.pipeline_update_callback = None  # Set by web orchestrator for pipeline stage updates
        self.mcp_log_callback = mcp_log_callback  # Callback for MCP server logs

        # Initialize core components
        self.router = Router()
        self.executor = AgentExecutor(project_id, [])
        self.performance_tracker = PerformanceTracker()

        # Initialize modular managers
        self.mcp = MCPIntegration(project_id)
        self.issue_manager = None  # Will be initialized after MCP
        self.planning_manager = PlanningManager()
        self.tech_stack_detector = TechStackDetector()

        # Initialize analytics
        config = {
            'llm_provider': llm_config.get('provider', 'unknown') if llm_config else 'unknown',
            'llm_model': llm_config.get('model', 'unknown') if llm_config else 'unknown',
            'llm_temperature': llm_config.get('temperature', 0.0) if llm_config else 0.0,
            'mode': 'implement_all'  # Will be updated in execute()
        }
        self.run_logger = RunLogger(project_id, config)
        self.csv_exporter = CSVExporter(Path('logs'))
        self.current_issue_tracker = None  # Will be created per issue

    async def initialize(self):
        """Initialize all components and managers"""
        try:
            # Get MCP tools and client (with optional logging callback)
            mcp_tools, client = await get_common_tools_and_client(self.mcp_log_callback)

            # Wrap client with SafeMCPClient for better error handling
            safe_client = SafeMCPClient(client)

            # Initialize MCP integration
            await self.mcp.initialize(mcp_tools, safe_client)

            # Initialize managers with tools
            self.issue_manager = IssueManager(self.project_id, mcp_tools)

            # Update executor with tools
            self.executor.tools = mcp_tools

            print(f"\n[SUPERVISOR] Initialized for project {self.project_id}")
            print(f"[MODULES] All managers loaded successfully")

            # Determine tech stack
            if self.provided_tech_stack:
                # User provided tech stack - normalize it
                detected_tech_stack = self.tech_stack_detector.from_user_input(self.provided_tech_stack)
                print(f"[TECH STACK] Using user-provided: {detected_tech_stack.get('backend', 'unknown')}")
            else:
                # Auto-detect from repository using MCP tools
                print(f"[TECH STACK] Auto-detecting from repository...")
                detected_tech_stack = await self.tech_stack_detector.detect_from_repository(
                    self.project_id,
                    mcp_tools
                )
                print(f"[TECH STACK] Detection complete: {detected_tech_stack}")

            # Store detected tech stack for Web GUI broadcast
            self.detected_tech_stack = detected_tech_stack

            # Store tech stack in executor for agents
            self.executor.tech_stack = detected_tech_stack

        except Exception as e:
            print(f"[SUPERVISOR] Initialization failed: {e}")
            raise

    async def _update_pipeline_stage(self, stage: str, status: str):
        """Send pipeline stage update to Web GUI if callback is set"""
        if self.pipeline_update_callback:
            try:
                await self.pipeline_update_callback(stage, status)
            except Exception as e:
                print(f"[WARN] Pipeline update callback failed: {e}")

    async def route_task(self, task_type: str, **kwargs) -> Any:
        """
        Route tasks to appropriate agents with performance tracking.
        """
        # Use router to validate and get routing decision
        routing_result = self.router.route_task(task_type, **kwargs)

        if not routing_result["success"]:
            raise ValueError(routing_result["error"])

        # Start performance tracking
        timing_id = self.performance_tracker.start_task_timing(routing_result["agent"], task_type)

        try:
            print(f"\n[SUPERVISOR] Delegating {task_type.upper()} task to {routing_result['agent']} agent...")
            print(f"[SUPERVISOR] Agent handoff initiated...")

            # Route to appropriate executor method
            result = None
            if task_type == "planning":
                result = await self.executor.execute_planning_agent(**kwargs)
                if result:
                    print(f"[SUPERVISOR] [OK] Planning agent handoff complete - plan acquired")
                    self.planning_manager.store_plan(result)
                else:
                    print(f"[SUPERVISOR] Planning agent handoff failed")

            elif task_type == "coding":
                result = await self.executor.execute_coding_agent(**kwargs)
                if result:
                    print(f"[SUPERVISOR] [OK] Coding agent handoff complete")
                else:
                    print(f"[SUPERVISOR] Coding agent handoff failed")

            elif task_type == "testing":
                result = await self.executor.execute_testing_agent(**kwargs)
                if result:
                    print(f"[SUPERVISOR] [OK] Testing agent handoff complete")
                else:
                    print(f"[SUPERVISOR] Testing agent handoff failed")

            elif task_type == "review":
                result = await self.executor.execute_review_agent(**kwargs)
                if result:
                    print(f"[SUPERVISOR] [OK] Review agent handoff complete")
                else:
                    print(f"[SUPERVISOR] Review agent handoff failed")

            # End performance tracking
            self.performance_tracker.end_task_timing(timing_id, success=bool(result))

            # Mark task completion in router
            self.router.complete_task(routing_result["agent"], success=bool(result))

            if result:
                print(f"[SUPERVISOR] {task_type.upper()} task completed successfully")
            else:
                print(f"[SUPERVISOR] [WARN] {task_type.upper()} task completed with issues")

            return result

        except Exception as e:
            # End performance tracking with error
            self.performance_tracker.end_task_timing(timing_id, success=False, error=str(e))

            # Mark task completion as failed
            self.router.complete_task(routing_result["agent"], success=False)

            print(f"[ERROR] {routing_result['agent']}: {e}")
            print(f"[SUPERVISOR] Agent coordination failed: {e}")
            raise Exception(f"Task {task_type} failed: {e}")

    async def implement_issue(self, issue: Dict, max_retries: int = None) -> bool:
        """
        Implement a single issue with retry logic.
        """
        issue_iid = get_issue_iid(issue)
        issue_title = issue.get("title", "Unknown")
        retries = max_retries if max_retries is not None else self.issue_manager.max_retries

        # Validate issue structure
        if not self.issue_manager.validate_issue(issue):
            print(f"[ERROR] Invalid issue structure for #{issue_iid}")
            return False

        # CRITICAL: Check if issue is already completed before starting workflow
        print(f"[WORKFLOW] Step 9.1: Checking if issue #{issue_iid} is already completed")
        print(f"[DEBUG] Issue title: {issue_title}")
        is_completed = await self.issue_manager.is_issue_completed(issue)
        print(f"[DEBUG] Completion check result: {is_completed}")
        if is_completed:
            print(f"[WORKFLOW] [OK] Issue #{issue_iid} already closed/merged - skipping")
            self.issue_manager.track_completed_issue(issue)
            return True  # Return success since work is already done

        # Create issue tracker for this issue
        self.current_issue_tracker = IssueTracker(self.run_logger.run_id, issue_iid)
        self.run_logger.add_issue(issue_iid)

        # Pass issue tracker to executor
        self.executor.issue_tracker = self.current_issue_tracker

        # Retry loop
        print(f"[WORKFLOW] Step 9.2: Starting retry loop (max {retries} attempts)")
        for attempt in range(retries):
            if attempt > 0:
                print(f"\n[WORKFLOW] [RETRY] Issue #{issue_iid} - Attempt {attempt + 1}/{retries}")
                print(f"[DEBUG] Retry delay: {self.issue_manager.retry_delay * attempt}s")
                await asyncio.sleep(self.issue_manager.retry_delay * attempt)

            print(f"\n{'='*70}")
            print(f"[WORKFLOW] Issue #{issue_iid}: {issue_title}")
            print(f"[WORKFLOW] Attempt {attempt + 1}/{retries}")
            print(f"{'='*70}")

            try:
                # Create feature branch name for this issue
                feature_branch = self.issue_manager.create_feature_branch_name(issue)
                print(f"[WORKFLOW] Step 9.3: Created feature branch: {feature_branch}")

                # Phase 1: Coding
                print(f"\n[WORKFLOW] Step 10: PHASE 1/3 - Coding Agent Execution")
                print(f"[DEBUG] Target branch: {feature_branch}")
                print(f"[DEBUG] Issue IID: {issue_iid}")
                await self._update_pipeline_stage("coding", "running")

                coding_result = await self.route_task(
                    "coding",
                    issue=issue,
                    branch=feature_branch
                )

                print(f"[DEBUG] Coding Agent result: {coding_result}")
                if not coding_result:
                    print(f"[WORKFLOW] [X] Coding phase failed - will retry")
                    await self._update_pipeline_stage("coding", "failed")
                    continue  # Retry the whole issue

                print(f"[WORKFLOW] [OK] Coding phase completed successfully")
                await self._update_pipeline_stage("coding", "completed")

                # Phase 2: Testing
                print(f"\n[WORKFLOW] Step 11: PHASE 2/3 - Testing Agent Execution")
                print(f"[DEBUG] Target branch: {feature_branch}")
                print(f"[DEBUG] Minimum coverage requirement: {self.min_coverage}%")
                await self._update_pipeline_stage("testing", "running")

                testing_result = await self.route_task(
                    "testing",
                    issue=issue,
                    branch=feature_branch
                )

                print(f"[DEBUG] Testing Agent result: {testing_result}")
                if not testing_result:
                    print(f"[WORKFLOW] [!] Testing phase failed - continuing to review")
                    await self._update_pipeline_stage("testing", "failed")
                    # Testing agent handles pipeline analysis via MCP tools
                else:
                    print(f"[WORKFLOW] [OK] Testing phase completed successfully")

                await self._update_pipeline_stage("testing", "completed")

                # Phase 3: Review & Merge Request
                print(f"\n[WORKFLOW] Step 12: PHASE 3/3 - Review Agent Execution")
                print(f"[DEBUG] Target branch: {feature_branch}")
                print(f"[DEBUG] Will validate pipeline and create MR")
                await self._update_pipeline_stage("review", "running")

                review_result = await self.route_task(
                    "review",
                    issue=issue,
                    branch=feature_branch
                )

                print(f"[DEBUG] Review Agent result: {review_result}")
                if review_result:
                    await self._update_pipeline_stage("review", "completed")
                    print(f"[WORKFLOW] [OK] Review phase completed - MR merged successfully")
                    print(f"\n[WORKFLOW] Step 13: Marking issue #{issue_iid} as complete")
                    self.issue_manager.track_completed_issue(issue)

                    # Finalize issue tracking and export to CSV
                    if self.current_issue_tracker:
                        print(f"[WORKFLOW] Step 14: Exporting analytics to CSV")
                        issue_report = self.current_issue_tracker.finalize_issue('completed')
                        self.csv_exporter.export_issue(self.run_logger.run_id, issue_report)
                        self.run_logger.record_success()
                        print(f"[DEBUG] Issue report exported successfully")

                    print(f"\n[WORKFLOW] [OK] Issue #{issue_iid} COMPLETED SUCCESSFULLY")
                    return True  # Success!
                else:
                    print(f"[WORKFLOW] [X] Review phase failed - will retry")
                    await self._update_pipeline_stage("review", "failed")

            except Exception as e:
                print(f"\n[WORKFLOW] [X] Exception occurred during implementation")
                print(f"[DEBUG] Error type: {type(e).__name__}")
                print(f"[DEBUG] Error message: {str(e)}")

                # Track error in issue tracker
                if self.current_issue_tracker:
                    print(f"[DEBUG] Recording error in issue tracker")
                    self.current_issue_tracker.errors.append({
                        'type': 'implementation_error',
                        'message': str(e),
                        'agent': 'supervisor',
                        'timestamp': datetime.now().isoformat()
                    })

                if attempt < retries - 1:
                    print(f"[WORKFLOW] Will retry (attempt {attempt + 1}/{retries})")
                    continue  # Retry
                else:
                    print(f"[WORKFLOW] [X] All retries exhausted - marking as failed")
                    return False  # Final failure

        # All retries failed - finalize issue as failed
        print(f"\n[WORKFLOW] [X] Issue #{issue_iid} FAILED after {retries} attempts")
        if self.current_issue_tracker:
            print(f"[WORKFLOW] Finalizing failed issue and exporting to CSV")
            issue_report = self.current_issue_tracker.finalize_issue('failed')
            self.csv_exporter.export_issue(self.run_logger.run_id, issue_report)
            self.run_logger.record_error()
            print(f"[DEBUG] Failed issue report exported")

        return False

    async def execute(self, mode: str = "implement", specific_issue: str = None, resume: bool = False):
        """
        Main execution flow using modular components.
        """
        print(f"\n{'='*70}")
        print(f"GITLAB AGENT SYSTEM - REFACTORED ORCHESTRATION")
        print(f"{'='*70}")
        print(f"Project: {self.project_id}")
        print(f"Mode: {mode}")
        print(f"State: {self.state.value}")

        # Update run logger with execution mode
        self.run_logger.mode = mode
        self.run_logger.specific_issue = specific_issue

        if resume:
            print("[WARNING] Resume functionality is not currently implemented")

        # Initialize
        try:
            self.state = ExecutionState.INITIALIZING
            await self.initialize()
        except Exception as e:
            print(f"[SUPERVISOR] Initialization failed: {e}")
            self.state = ExecutionState.FAILED
            return

        # Phase 1: Planning
        self.state = ExecutionState.PLANNING
        await self._update_pipeline_stage("planning", "running")
        print("\n" + "="*60)
        print("PHASE 1: PLANNING & ANALYSIS")
        print("="*60)
        print(f"[WORKFLOW] Step 1: Planning Agent Execution")
        print(f"[DEBUG] Execution mode: {mode}")
        print(f"[DEBUG] Apply changes: {mode in ['implement', 'single']}")

        apply_changes = mode in ["implement", "single"]

        # Run planning analysis
        print(f"[WORKFLOW] Delegating to Planning Agent...")
        success = await self.planning_manager.execute_planning_with_retry(
            self.route_task,
            apply_changes
        )

        if not success:
            print("[ERROR] Planning analysis failed after retries")
            print("[WORKFLOW] [FAILED] Planning Agent execution FAILED")
            await self._update_pipeline_stage("planning", "failed")
            self.state = ExecutionState.FAILED
            return

        print("[WORKFLOW] [OK] Planning Agent execution successful")
        await self._update_pipeline_stage("planning", "completed")

        print(f"\n[DEBUG] ========== POST-PLANNING CHECKPOINT ==========")
        print(f"[DEBUG] Current mode: {mode}")
        print(f"[DEBUG] Checking if mode == 'analyze': {mode == 'analyze'}")

        if mode == "analyze":
            print("\n[COMPLETE] Analysis done. Run with --apply to implement.")
            print("[DEBUG] ========== EARLY EXIT: ANALYZE MODE ==========")
            self.state = ExecutionState.COMPLETED
            await self.show_summary()
            return

        print(f"[DEBUG] Mode is '{mode}' - proceeding to implementation preparation")

        # Phase 1.5: Load Planning Documents from Master
        # Planning Agent commits directly to master, so load parsed ORCH_PLAN.json
        print(f"\n[WORKFLOW] Step 2: Loading ORCH_PLAN.json from master")
        print("[DEBUG] Planning Agent commits directly to master - loading structured plan")
        print("[DEBUG] Loading from: docs/ORCH_PLAN.json on master branch")

        try:
            plan_loaded = await self.planning_manager.load_plan_from_repository(
                self.mcp,
                self.project_id,
                ref="master"
            )

            if plan_loaded:
                print("[WORKFLOW] [OK] ORCH_PLAN.json loaded successfully")
                plan = self.planning_manager.get_current_plan()
                if plan and isinstance(plan, dict) and 'implementation_order' in plan:
                    order = plan['implementation_order']
                    print(f"[DEBUG] Implementation order: {order}")
                    print(f"[DEBUG] Total issues in plan: {len(order)}")
                else:
                    print("[DEBUG] Plan structure: unknown or missing implementation_order")
            else:
                print("[WORKFLOW] [WARNING] Could not load ORCH_PLAN.json - will use fallback prioritization")

        except Exception as e:
            print(f"[WARNING] Could not load planning documents: {str(e)}")
            print(f"[DEBUG] Exception type: {type(e).__name__}")
            print("[WORKFLOW] [WARNING] Using fallback prioritization")

        # Phase 2: Implementation Preparation
        print("\n" + "="*60)
        print("PHASE 2: IMPLEMENTATION PREPARATION")
        print("="*60)

        # Load ORCH_PLAN.json if not already loaded (fallback for resumed sessions)
        if not self.planning_manager.get_current_plan():
            print("[WORKFLOW] Plan not in memory, attempting to load from repository...")
            await self.planning_manager.load_plan_from_repository(
                self.mcp,
                self.project_id,
                ref="master"
            )

        # Fetch issues from GitLab
        print(f"\n[DEBUG] ========== ISSUE FETCHING CHECKPOINT ==========")
        print(f"\n[WORKFLOW] Step 6: Fetching all open issues from GitLab")
        print(f"[DEBUG] Project ID: {self.project_id}")
        print(f"[DEBUG] Issue state filter: opened")

        all_gitlab_issues = await self.issue_manager.fetch_gitlab_issues()
        print(f"[DEBUG] fetch_gitlab_issues() returned: {type(all_gitlab_issues)}")
        print(f"[DEBUG] Number of issues returned: {len(all_gitlab_issues) if all_gitlab_issues else 0}")

        if not all_gitlab_issues:
            print("[WORKFLOW] [WARNING] No open issues found in GitLab")
            print("[DEBUG] Possible reasons: all issues closed, project has no issues, or API error")
            print("[DEBUG] ========== EARLY EXIT: NO ISSUES FOUND ==========")
            await self.show_summary()
            return

        print(f"[WORKFLOW] [OK] Fetched {len(all_gitlab_issues)} open issues from GitLab")
        print(f"[DEBUG] Issue IIDs: {[get_issue_iid(i) for i in all_gitlab_issues]}")

        # Apply planning prioritization
        print(f"\n[DEBUG] ========== PRIORITIZATION CHECKPOINT ==========")
        print(f"\n[WORKFLOW] Step 7: Applying ORCH_PLAN.json priority order")
        current_plan = self.planning_manager.get_current_plan()

        print(f"[DEBUG] current_plan type: {type(current_plan)}")
        print(f"[DEBUG] current_plan is not None: {current_plan is not None}")

        if current_plan and isinstance(current_plan, dict) and 'implementation_order' in current_plan:
            print(f"[DEBUG] Using ORCH_PLAN.json with {len(current_plan['implementation_order'])} issues")
            print(f"[DEBUG] Implementation order issue IIDs: {current_plan['implementation_order']}")
        else:
            print(f"[DEBUG] Using fallback prioritization (no ORCH_PLAN.json)")

        print(f"[DEBUG] Calling apply_planning_prioritization()...")
        print(f"[DEBUG] Input: {len(all_gitlab_issues)} GitLab issues")

        issues = await self.planning_manager.apply_planning_prioritization(
            all_gitlab_issues,
            self.planning_manager.get_current_plan(),
            self.issue_manager.is_issue_completed
        )

        print(f"[DEBUG] apply_planning_prioritization() returned: {type(issues)}")
        print(f"[DEBUG] Number of issues after filtering: {len(issues) if issues else 0}")

        print(f"\n[DEBUG] ========== FILTERING RESULTS CHECKPOINT ==========")
        print(f"[DEBUG] Checking if issues list is truthy: {bool(issues)}")
        print(f"[DEBUG] issues is None: {issues is None}")
        print(f"[DEBUG] issues == []: {issues == []}")

        if issues:
            print(f"\n[WORKFLOW] Step 8: Issue Filtering Results")
            print(f"[DEBUG] Total fetched from GitLab: {len(all_gitlab_issues)} open issues")
            print(f"[DEBUG] After prioritization & filtering: {len(issues)} issues")
            print(f"[DEBUG] Filtered out: {len(all_gitlab_issues) - len(issues)} completed/merged issues")

            # Show which issues were filtered out
            filtered_out_iids = set(get_issue_iid(i) for i in all_gitlab_issues) - set(get_issue_iid(i) for i in issues)
            if filtered_out_iids:
                print(f"[DEBUG] Filtered out issue IIDs: {sorted(filtered_out_iids)}")

            print(f"[WORKFLOW] [OK] {len(issues)} issues ready for implementation")
            print(f"\n[PRIORITY] Implementation order:")
            # Show issue details in priority order
            for idx, issue in enumerate(issues, 1):
                issue_iid = get_issue_iid(issue)
                title = issue.get('title', 'No title')
                print(f"  {idx}. Issue #{issue_iid}: {title}")
        else:
            print("[WORKFLOW] [WARNING] No issues need implementation (all completed or merged)")
            print("[DEBUG] All issues have been filtered out - nothing to do")
            print(f"[DEBUG] Total GitLab issues: {len(all_gitlab_issues)}")
            print(f"[DEBUG] Issues after filtering: {len(issues) if issues else 0}")
            print("[DEBUG] ========== EARLY EXIT: ALL ISSUES FILTERED OUT ==========")
            await self.show_summary()
            return

        # Phase 3: Implementation
        print(f"\n[DEBUG] ========== PHASE 3 ENTRY CHECKPOINT ==========")
        print(f"[DEBUG] About to check if issues list exists for Phase 3")
        print(f"[DEBUG] issues is truthy: {bool(issues)}")
        print(f"[DEBUG] len(issues): {len(issues) if issues else 'N/A'}")

        if issues:
            print("\n" + "="*60)
            print("PHASE 3: IMPLEMENTATION")
            print("="*60)
            print(f"[DEBUG] Entered Phase 3 implementation block")

            # Get issues to implement
            if specific_issue:
                # Single issue mode
                print(f"[DEBUG] Single issue mode: filtering for issue #{specific_issue}")
                issues_to_implement = [
                    i for i in issues
                    if str(i.get("iid")) == str(specific_issue)
                ]
                if not issues_to_implement:
                    print(f"[ERROR] Issue {specific_issue} not found or already completed")
                    print(f"[DEBUG] Available issues: {[get_issue_iid(i) for i in issues]}")
                    return
                print(f"[DEBUG] Found issue #{specific_issue} in queue")
            else:
                # All issues mode
                print(f"[DEBUG] All issues mode: implementing all {len(issues)} issues")
                issues_to_implement = issues

            print(f"\n[WORKFLOW] Will implement {len(issues_to_implement)} issues sequentially")
            print(f"[DEBUG] Execution sequence:")

            # Show issue titles for clarity
            for idx, issue in enumerate(issues_to_implement, 1):
                iid = get_issue_iid(issue)
                title = issue.get('title', 'Unknown')
                print(f"  {idx}. Issue #{iid}: {title}")

            # Implement each issue
            print(f"\n[DEBUG] ========== ISSUE LOOP ENTRY CHECKPOINT ==========")
            print(f"\n[WORKFLOW] Starting issue implementation loop")
            print(f"[DEBUG] Total issues to implement: {len(issues_to_implement)}")
            print(f"[DEBUG] Loop will iterate {len(issues_to_implement)} times")

            for idx, issue in enumerate(issues_to_implement, 1):
                print(f"\n[DEBUG] ========== LOOP ITERATION {idx}/{len(issues_to_implement)} ==========")
                print(f"[DEBUG] Processing issue index: {idx}")
                issue_iid = get_issue_iid(issue)
                issue_title = issue.get('title', 'Unknown')

                # Skip if already completed
                if any((get_issue_iid(c) if isinstance(c, dict) else c) == issue_iid
                       for c in self.issue_manager.completed_issues):
                    print(f"\n[SKIP] Issue #{issue_iid} already completed in previous run")
                    print(f"[DEBUG] Skipping to next issue")
                    continue

                print(f"\n{'='*60}")
                print(f"[WORKFLOW] [{idx}/{len(issues_to_implement)}] Processing Issue #{issue_iid}")
                print(f"{'='*60}")
                print(f"[DEBUG] Issue title: {issue_title}")
                print(f"[DEBUG] Issue state: {issue.get('state', 'unknown')}")
                print(f"\n[WORKFLOW] Step 9.{idx}: Checking completion status for Issue #{issue_iid}")

                # Use retry logic for resilience
                success = await self.implement_issue(issue)

                if success:
                    # Already tracked in implement_issue
                    print(f"\n[WORKFLOW] [OK] Issue #{issue_iid} completed successfully")
                    print(f"[DEBUG] Completed issues so far: {len(self.issue_manager.completed_issues)}")
                else:
                    print(f"\n[WORKFLOW] [FAILED] Issue #{issue_iid} FAILED after retries")
                    self.issue_manager.track_failed_issue(issue)
                    print(f"[DEBUG] Failed issues so far: {len(self.issue_manager.failed_issues)}")

                # Brief pause between issues
                if idx < len(issues_to_implement):
                    print(f"\n[WORKFLOW] Pausing 3 seconds before next issue...")
                    print(f"[DEBUG] Next: Issue #{get_issue_iid(issues_to_implement[idx])} ({idx+1}/{len(issues_to_implement)})")
                    await asyncio.sleep(3)

            print(f"\n[DEBUG] ========== ISSUE LOOP COMPLETED ==========")
            print(f"[DEBUG] All {len(issues_to_implement)} issues processed")

        # Final state and summary
        print(f"\n[DEBUG] ========== FINAL STATE CHECKPOINT ==========")
        print(f"[DEBUG] About to set state to COMPLETING")
        self.state = ExecutionState.COMPLETING
        print(f"[DEBUG] Calling show_summary()...")
        await self.show_summary()
        print(f"[DEBUG] show_summary() completed")

        # Set final state
        stats = self.issue_manager.get_summary_stats()
        if stats['failed'] == 0 and stats['completed'] > 0:
            self.state = ExecutionState.COMPLETED
            print("\n[OK] ORCHESTRATION COMPLETED SUCCESSFULLY")
        elif stats['completed'] > 0:
            self.state = ExecutionState.COMPLETED
            print("\n[WARN] ORCHESTRATION COMPLETED WITH SOME FAILURES")
        else:
            self.state = ExecutionState.FAILED
            print("\nORCHESTRATION FAILED")

        # Finalize run and export to CSV
        final_status = 'completed' if self.state == ExecutionState.COMPLETED else 'failed'
        self.run_logger.finalize_run(final_status)

        # Export run summary to CSV
        run_data = {
            'run_id': self.run_logger.run_id,
            'project_id': self.project_id,
            'start_time': self.run_logger.start_time.isoformat(),
            'end_time': self.run_logger.end_time.isoformat() if self.run_logger.end_time else None,
            'duration_seconds': (self.run_logger.end_time - self.run_logger.start_time).total_seconds() if self.run_logger.end_time else 0,
            'llm_configuration': self.run_logger.llm_config,
            'execution_mode': self.run_logger.mode,
            'specific_issue': self.run_logger.specific_issue,
            'status': final_status,
            'total_issues': len(self.run_logger.issues_processed),
            'total_successes': self.run_logger.total_successes,
            'total_errors': self.run_logger.total_errors,
            'success_rate': (self.run_logger.total_successes / len(self.run_logger.issues_processed) * 100) if self.run_logger.issues_processed else 0
        }
        self.csv_exporter.export_run(run_data)

        print(f"\n[ANALYTICS] CSV files exported to: {self.csv_exporter.csv_dir}")

        # Clean up
        await self.cleanup()

    async def show_summary(self):
        """Show execution summary with detailed metrics"""
        print("\n" + "="*70)
        print("EXECUTION SUMMARY")
        print("="*70)

        # Get issue implementation results from issue manager
        stats = self.issue_manager.get_summary_stats()

        if stats['total_processed'] > 0:
            print(f"\nISSUE IMPLEMENTATION:")
            print(f"  Total Processed: {stats['total_processed']}")
            print(f"  [OK] Completed: {stats['completed']}")
            print(f"  Failed: {stats['failed']}")
            print(f"  Success Rate: {stats['success_rate']:.1f}%")

            if stats['completed_issues']:
                print(f"\n[OK] Completed Issues:")
                for issue in stats['completed_issues']:
                    print(f"    - #{issue.get('iid')}: {issue.get('title', 'Unknown')}")

            if stats['failed_issues']:
                print(f"\nFailed Issues:")
                for issue in stats['failed_issues']:
                    print(f"    - #{issue.get('iid')}: {issue.get('title', 'Unknown')}")

        # Show performance metrics
        perf_summary = self.performance_tracker.get_performance_summary()
        print(f"\n[PERFORMANCE] {perf_summary}")

        # Show execution statistics
        exec_summary = self.executor.get_execution_summary()
        print(f"[EXECUTION] {exec_summary}")

        # Show final state
        print(f"\n[FINAL STATE] {self.state.value}")

    async def cleanup(self):
        """Clean up resources."""
        await self.mcp.cleanup()


# Helper function for running supervisor
async def run_supervisor(
    project_id: str,
    mode: str = "implement",
    specific_issue: str = None,
    resume_from: str = None,
    tech_stack: dict = None,
    llm_config: dict = None
):
    """
    Helper function to run supervisor with the specified parameters.
    """
    supervisor = Supervisor(project_id, tech_stack=tech_stack, llm_config=llm_config)

    # Map mode to supervisor execution mode
    exec_mode = "implement" if mode == "implement" else "analyze"

    await supervisor.execute(mode=exec_mode, specific_issue=specific_issue)