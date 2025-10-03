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
        issue_id = issue.get("iid")
        issue_title = issue.get("title", "Unknown")
        retries = max_retries if max_retries is not None else self.issue_manager.max_retries

        # Validate issue structure
        if not self.issue_manager.validate_issue(issue):
            print(f"[ERROR] Invalid issue structure for #{issue_id}")
            return False

        # CRITICAL: Check if issue is already completed before starting workflow
        print(f"[CHECK] Verifying completion status for issue #{issue_id}...")
        is_completed = await self.issue_manager.is_issue_completed(issue)
        if is_completed:
            print(f"[SKIP] Issue #{issue_id} is already closed/merged - skipping implementation")
            self.issue_manager.track_completed_issue(issue)
            return True  # Return success since work is already done

        # Create issue tracker for this issue
        self.current_issue_tracker = IssueTracker(self.run_logger.run_id, issue_id)
        self.run_logger.add_issue(issue_id)

        # Pass issue tracker to executor
        self.executor.issue_tracker = self.current_issue_tracker

        # Retry loop
        for attempt in range(retries):
            if attempt > 0:
                print(f"[RETRY] Issue #{issue_id} attempt {attempt + 1}/{retries}")
                await asyncio.sleep(self.issue_manager.retry_delay * attempt)

            print(f"\n[ISSUE #{issue_id}] Starting: {issue_title}")
            print(f"[ISSUE #{issue_id}] Implementation starting")

            try:
                # Create feature branch name for this issue
                feature_branch = self.issue_manager.create_feature_branch_name(issue)

                # Phase 1: Coding
                await self._update_pipeline_stage("coding", "running")
                print(f"[ISSUE #{issue_id}] Phase 1/3: Coding...")
                print(f"[ISSUE #{issue_id}] Working on branch: {feature_branch}")
                coding_result = await self.route_task(
                    "coding",
                    issue=issue,
                    branch=feature_branch
                )

                if not coding_result:
                    print(f"[ISSUE #{issue_id}] Coding phase failed")
                    await self._update_pipeline_stage("coding", "failed")
                    continue  # Retry the whole issue

                await self._update_pipeline_stage("coding", "completed")

                # Phase 2: Testing
                await self._update_pipeline_stage("testing", "running")
                print(f"[ISSUE #{issue_id}] Phase 2/3: Testing...")
                print(f"[ISSUE #{issue_id}] Running tests with minimum {self.min_coverage}% coverage requirement")

                testing_result = await self.route_task(
                    "testing",
                    issue=issue,
                    branch=feature_branch
                )

                if not testing_result:
                    print(f"[ISSUE #{issue_id}] [WARN] Testing phase failed")
                    await self._update_pipeline_stage("testing", "failed")
                    # Testing agent handles pipeline analysis via MCP tools

                await self._update_pipeline_stage("testing", "completed")

                # Phase 3: Review & Merge Request
                await self._update_pipeline_stage("review", "running")
                print(f"[ISSUE #{issue_id}] Phase 3/3: Review & MR...")
                # Review agent checks pipeline status via MCP tools

                review_result = await self.route_task(
                    "review",
                    issue=issue,
                    branch=feature_branch
                )

                if review_result:
                    await self._update_pipeline_stage("review", "completed")
                    print(f"[ISSUE #{issue_id}] [OK] Successfully implemented")
                    self.issue_manager.track_completed_issue(issue)

                    # Finalize issue tracking and export to CSV
                    if self.current_issue_tracker:
                        issue_report = self.current_issue_tracker.finalize_issue('completed')
                        self.csv_exporter.export_issue(self.run_logger.run_id, issue_report)
                        self.run_logger.record_success()

                    return True  # Success!
                else:
                    await self._update_pipeline_stage("review", "failed")

            except Exception as e:
                print(f"[ISSUE #{issue_id}] Implementation failed: {e}")

                # Track error in issue tracker
                if self.current_issue_tracker:
                    self.current_issue_tracker.errors.append({
                        'type': 'implementation_error',
                        'message': str(e),
                        'agent': 'supervisor',
                        'timestamp': datetime.now().isoformat()
                    })

                if attempt < retries - 1:
                    continue  # Retry
                return False  # Final failure

        # All retries failed - finalize issue as failed
        if self.current_issue_tracker:
            issue_report = self.current_issue_tracker.finalize_issue('failed')
            self.csv_exporter.export_issue(self.run_logger.run_id, issue_report)
            self.run_logger.record_error()

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

        apply_changes = mode in ["implement", "single"]

        # Run planning analysis
        success = await self.planning_manager.execute_planning_with_retry(
            self.route_task,
            apply_changes
        )

        if not success:
            print("[ERROR] Planning analysis failed after retries")
            await self._update_pipeline_stage("planning", "failed")
            self.state = ExecutionState.FAILED
            return

        await self._update_pipeline_stage("planning", "completed")

        # Store the planning result
        if hasattr(self.executor, 'current_plan') and self.executor.current_plan:
            self.planning_manager.store_plan(self.executor.current_plan)

        if mode == "analyze":
            print("\n[COMPLETE] Analysis done. Run with --apply to implement.")
            self.state = ExecutionState.COMPLETED
            await self.show_summary()
            return

        # Phase 1.5: Review and Merge Planning Work (if branch exists)
        # Check if planning-structure branch exists and needs merging
        try:
            branches = await self.mcp_manager.run_tool("list_branches", {
                "project_id": str(self.project_id)
            })

            # Check if planning-structure branch exists
            planning_branch_exists = False
            if branches and isinstance(branches, list):
                for branch in branches:
                    if branch.get('name', '').startswith('planning-structure'):
                        planning_branch_exists = True
                        planning_branch = branch.get('name')
                        break

            if planning_branch_exists:
                print("\n" + "="*60)
                print("PHASE 1.5: REVIEW PLANNING WORK")
                print("="*60)
                print(f"[REVIEW] Found planning branch: {planning_branch}")
                print("[REVIEW] Delegating to Review Agent for merge...")

                # Execute review agent for planning work
                review_success = await self.route_task(
                    "REVIEW",
                    {"work_branch": planning_branch, "issue_id": "planning", "type": "planning"}
                )

                if not review_success:
                    print("[WARNING] Planning review failed, but continuing...")
                else:
                    print("[REVIEW] Planning work reviewed and merged successfully")
        except Exception as e:
            print(f"[WARNING] Could not check for planning branch: {str(e)}")

        # Phase 2: Implementation Preparation
        print("\n" + "="*60)
        print("PHASE 2: IMPLEMENTATION PREPARATION")
        print("="*60)

        # Fetch issues from GitLab
        print("[ISSUES] Fetching issues from GitLab...")
        all_gitlab_issues = await self.issue_manager.fetch_gitlab_issues()

        if not all_gitlab_issues:
            print("[ISSUES] No open issues found")
            await self.show_summary()
            return

        print(f"[ISSUES] Found {len(all_gitlab_issues)} open issues from GitLab")

        # Apply planning prioritization
        issues = await self.planning_manager.apply_planning_prioritization(
            all_gitlab_issues,
            self.planning_manager.get_current_plan(),
            self.issue_manager.is_issue_completed
        )

        if issues:
            print(f"[ISSUES] After planning prioritization and filtering: {len(issues)} issues to implement")
            # Show issue details in priority order
            for issue in issues[:5]:  # Show first 5
                issue_id = issue.get('iid') or issue.get('id')
                title = issue.get('title', 'No title')
                print(f"  - Issue #{issue_id}: {title}")
        else:
            print("[ISSUES] No issues need implementation (all completed or merged)")
            await self.show_summary()
            return

        # Phase 3: Implementation
        if issues:
            print("\n" + "="*60)
            print("PHASE 3: IMPLEMENTATION")
            print("="*60)

            # Get issues to implement
            if specific_issue:
                # Single issue mode
                issues_to_implement = [
                    i for i in issues
                    if str(i.get("iid")) == str(specific_issue)
                ]
                if not issues_to_implement:
                    print(f"[ERROR] Issue {specific_issue} not found or already completed")
                    return
            else:
                # All issues mode
                issues_to_implement = issues

            print(f"[PLAN] Will implement {len(issues_to_implement)} issues")

            # Show issue titles for clarity
            for issue in issues_to_implement[:5]:  # Show first 5
                print(f"  - Issue #{issue.get('iid')}: {issue.get('title', 'Unknown')}")

            # Implement each issue
            for idx, issue in enumerate(issues_to_implement, 1):
                issue_id = issue.get('iid')

                # Skip if already completed
                if any((c.get('iid') if isinstance(c, dict) else c) == issue_id
                       for c in self.issue_manager.completed_issues):
                    print(f"\n[SKIP] Issue #{issue_id} already completed in previous run")
                    continue

                print(f"\n[PROGRESS] {idx}/{len(issues_to_implement)}")

                # Use retry logic for resilience
                success = await self.implement_issue(issue)

                if success:
                    # Already tracked in implement_issue
                    print(f"[SUCCESS] [OK] Issue #{issue_id} completed successfully")
                else:
                    self.issue_manager.track_failed_issue(issue)

                # Brief pause between issues
                if idx < len(issues_to_implement):
                    print("\n[PAUSE] 3 seconds between issues...")
                    await asyncio.sleep(3)

        # Final state and summary
        self.state = ExecutionState.COMPLETING
        await self.show_summary()

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