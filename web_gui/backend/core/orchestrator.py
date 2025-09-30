"""
System orchestrator that integrates with the existing supervisor system
Handles real-time monitoring and control
"""

import asyncio
import sys
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import traceback
import io
import os
from contextlib import redirect_stdout, redirect_stderr

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.orchestrator.supervisor import Supervisor
from .websocket import ConnectionManager
from .monitor import AgentMonitor, ToolMonitor


class SystemOrchestrator:
    """Orchestrates the autonomous system with real-time monitoring"""

    def __init__(self, ws_manager: ConnectionManager):
        self.ws_manager = ws_manager
        self.supervisor: Optional[Supervisor] = None
        self.running = False
        self.current_config = None
        self.start_time = None
        self.current_issue = None
        self.current_stage = None
        self.current_agent = None

        # Initialize monitors
        self.agent_monitor = AgentMonitor(ws_manager)
        self.tool_monitor = ToolMonitor(ws_manager)

        # Statistics
        self.stats = {
            "total_issues": 0,
            "processed_issues": 0,
            "successful_issues": 0,
            "failed_issues": 0,
            "total_time": 0,
            "agent_calls": 0,
            "tool_calls": 0
        }

    async def start(self, config: Dict[str, Any]):
        """Start the autonomous system"""
        if self.running:
            await self.ws_manager.send_error("System is already running")
            return

        try:
            self.current_config = config
            self.running = True
            self.start_time = datetime.now()

            await self.ws_manager.send_system_status({
                "running": True,
                "message": "System starting...",
                "config": config
            })

            # Create and execute supervisor (like CLI)
            await self._execute_supervisor_like_cli(config)

            await self.ws_manager.send_success("System completed successfully")

        except Exception as e:
            error_msg = f"System error: {str(e)}"
            print(f"[ERROR] {error_msg}")
            traceback.print_exc()
            await self.ws_manager.send_error(error_msg)
        finally:
            self.running = False
            await self.ws_manager.send_system_status({
                "running": False,
                "message": "System stopped"
            })

    async def stop(self):
        """Stop the running system"""
        if not self.running:
            await self.ws_manager.send_error("System is not running")
            return

        self.running = False
        await self.ws_manager.send_system_status({
            "running": False,
            "message": "System stopping..."
        })

        # Clean up supervisor
        if self.supervisor:
            # Supervisor cleanup logic here
            pass

        await self.ws_manager.send_success("System stopped")

    async def _execute_supervisor_like_cli(self, config: Dict[str, Any]):
        """Execute supervisor using the same pattern as CLI"""
        project_id = config.get("project_id")
        print(f"[DEBUG] Received config in _execute_supervisor_like_cli: {config}")
        print(f"[DEBUG] Extracted project_id: {project_id}")

        if not project_id:
            raise ValueError("Project ID is required to initialize the system")

        tech_stack = config.get("tech_stack")
        mode = config.get("mode", "implement_all")
        specific_issue = config.get("specific_issue")

        # Map web GUI modes to supervisor modes
        if mode == "implement_all":
            supervisor_mode = "implement"
        elif mode == "single_issue":
            supervisor_mode = "implement"
        elif mode == "analysis":
            supervisor_mode = "analyze"
        else:
            supervisor_mode = "implement"

        await self.ws_manager.send_agent_output(
            "System",
            f"Initializing supervisor for project {project_id}",
            "info"
        )

        # Create supervisor instance
        self.supervisor = Supervisor(project_id, tech_stack)

        # Set additional configuration
        if config.get('min_coverage'):
            self.supervisor.min_coverage = config.get('min_coverage')

        # Execute supervisor (like CLI does)
        # NOTE: Removed output capture to prevent stdout/stderr interference with tools
        # Output capture was causing async/sync issues and breaking tool results
        await self.supervisor.execute(mode=supervisor_mode, specific_issue=specific_issue)

        await self.ws_manager.send_success("Supervisor execution completed")

    async def _initialize_supervisor(self, config: Dict[str, Any]):
        """Initialize the supervisor with configuration"""
        print(f"[DEBUG] Received config in _initialize_supervisor: {config}")
        project_id = config.get("project_id")
        print(f"[DEBUG] Extracted project_id: {project_id}")
        if not project_id:
            raise ValueError("Project ID is required to initialize the system")

        tech_stack = config.get("tech_stack")

        await self.ws_manager.send_agent_output(
            "System",
            f"Initializing supervisor for project {project_id}",
            "info"
        )

        # Create supervisor instance with project ID and tech stack
        self.supervisor = Supervisor(project_id, tech_stack)

        # Set additional configuration
        if config.get('min_coverage'):
            self.supervisor.min_coverage = config.get('min_coverage')

        # Initialize the supervisor components
        # NOTE: Removed output capture to prevent stdout/stderr interference
        await self.supervisor.initialize()

        await self.ws_manager.send_success("Supervisor initialized")

    async def _process_all_issues(self):
        """Process all open issues"""
        await self.ws_manager.send_pipeline_update("fetch_issues", "running")

        # Get open issues
        issues = await self._get_open_issues()
        self.stats["total_issues"] = len(issues)

        await self.ws_manager.send_pipeline_update("fetch_issues", "completed", {
            "count": len(issues)
        })

        # Process each issue
        for i, issue in enumerate(issues):
            if not self.running:
                break

            progress = (i / len(issues)) * 100
            await self.ws_manager.send_system_status({
                "running": True,
                "progress": progress,
                "current_issue": issue,
                "stats": self.stats
            })

            await self._process_issue(issue)

    async def _process_single_issue(self, issue_number: int):
        """Process a single specific issue"""
        # Get the specific issue
        issue = await self._get_issue(issue_number)
        if not issue:
            raise ValueError(f"Issue #{issue_number} not found")

        self.stats["total_issues"] = 1
        await self._process_issue(issue)

    async def _process_issue(self, issue: Dict[str, Any]):
        """Process a single issue through the pipeline"""
        self.current_issue = issue
        issue_id = issue.get("iid", issue.get("id"))

        await self.ws_manager.send_issue_update(issue_id, "processing", issue)

        try:
            # Planning stage
            await self._run_stage("planning", issue)

            # Coding stage
            await self._run_stage("coding", issue)

            # Testing stage
            await self._run_stage("testing", issue)

            # Review stage
            await self._run_stage("review", issue)

            # Issue completed
            self.stats["successful_issues"] += 1
            await self.ws_manager.send_issue_update(issue_id, "completed")

        except Exception as e:
            self.stats["failed_issues"] += 1
            await self.ws_manager.send_issue_update(issue_id, "failed", {
                "error": str(e)
            })
            raise

        finally:
            self.stats["processed_issues"] += 1
            self.current_issue = None

    async def _run_stage(self, stage: str, issue: Dict[str, Any]):
        """Run a specific pipeline stage"""
        self.current_stage = stage
        self.current_agent = f"{stage}_agent"

        await self.ws_manager.send_pipeline_update(stage, "running")

        try:
            # Capture agent output
            output_buffer = io.StringIO()

            with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                if stage == "planning":
                    success = await self._run_planning(issue)
                elif stage == "coding":
                    success = await self._run_coding(issue)
                elif stage == "testing":
                    success = await self._run_testing(issue)
                elif stage == "review":
                    success = await self._run_review(issue)
                else:
                    raise ValueError(f"Unknown stage: {stage}")

            # Send captured output
            output = output_buffer.getvalue()
            if output:
                await self.ws_manager.send_agent_output(
                    self.current_agent,
                    output,
                    "success" if success else "error"
                )

            if not success:
                raise Exception(f"{stage.title()} stage failed")

            await self.ws_manager.send_pipeline_update(stage, "completed")

        except Exception as e:
            await self.ws_manager.send_pipeline_update(stage, "failed", {
                "error": str(e)
            })
            raise

        finally:
            self.current_stage = None
            self.current_agent = None
            self.stats["agent_calls"] += 1

    async def _run_planning(self, issue: Dict[str, Any]) -> bool:
        """Run planning agent"""
        with self.agent_monitor.capture_output("Planning Agent"):
            apply = self.current_config.get("mode") != "analysis"
            if hasattr(self.supervisor, 'executor'):
                return await self.supervisor.executor.execute_planning_agent(
                    issue=issue,
                    apply=apply,
                    show_tokens=True
                )
            return False

    async def _run_coding(self, issue: Dict[str, Any]) -> bool:
        """Run coding agent"""
        with self.agent_monitor.capture_output("Coding Agent"):
            branch = f"feature/issue-{issue.get('iid', issue.get('id'))}"
            if hasattr(self.supervisor, 'executor'):
                return await self.supervisor.executor.execute_coding_agent(
                    issue=issue,
                    branch=branch,
                    show_tokens=True
                )
            return False

    async def _run_testing(self, issue: Dict[str, Any]) -> bool:
        """Run testing agent"""
        with self.agent_monitor.capture_output("Testing Agent"):
            branch = f"feature/issue-{issue.get('iid', issue.get('id'))}"
            if hasattr(self.supervisor, 'executor'):
                return await self.supervisor.executor.execute_testing_agent(
                    issue=issue,
                    branch=branch,
                    show_tokens=True
                )
            return False

    async def _run_review(self, issue: Dict[str, Any]) -> bool:
        """Run review agent"""
        with self.agent_monitor.capture_output("Review Agent"):
            branch = f"feature/issue-{issue.get('iid', issue.get('id'))}"
            if hasattr(self.supervisor, 'executor'):
                return await self.supervisor.executor.execute_review_agent(
                    issue=issue,
                    branch=branch,
                    show_tokens=True
                )
            return False

    async def _run_analysis(self):
        """Run analysis mode (planning only)"""
        # Get open issues for analysis
        issues = await self._get_open_issues()

        for issue in issues[:5]:  # Analyze first 5 issues
            if not self.running:
                break

            await self._run_stage("planning", issue)

    async def _get_open_issues(self) -> list:
        """Get open issues from GitLab"""
        if self.supervisor and hasattr(self.supervisor, 'issue_manager') and self.supervisor.issue_manager:
            return await self.supervisor.issue_manager.fetch_gitlab_issues()
        return []

    async def _get_issue(self, issue_number: int) -> Optional[Dict]:
        """Get a specific issue"""
        if self.supervisor and self.supervisor.issue_manager:
            return await self.supervisor.issue_manager.get_issue(issue_number)
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "running": self.running,
            "current_stage": self.current_stage,
            "current_agent": self.current_agent,
            "current_issue": self.current_issue,
            "progress": self._calculate_progress(),
            "start_time": self.start_time,
            "stats": self.stats
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            **self.stats,
            "uptime": self._calculate_uptime(),
            "success_rate": self._calculate_success_rate()
        }

    def _calculate_progress(self) -> float:
        """Calculate overall progress"""
        if self.stats["total_issues"] == 0:
            return 0.0
        return (self.stats["processed_issues"] / self.stats["total_issues"]) * 100

    def _calculate_uptime(self) -> int:
        """Calculate system uptime in seconds"""
        if not self.start_time:
            return 0
        return int((datetime.now() - self.start_time).total_seconds())

    def _calculate_success_rate(self) -> float:
        """Calculate success rate"""
        if self.stats["processed_issues"] == 0:
            return 0.0
        return (self.stats["successful_issues"] / self.stats["processed_issues"]) * 100

    async def cleanup(self):
        """Clean up resources"""
        if self.supervisor:
            # Cleanup supervisor resources
            pass


# Global orchestrator instance
_orchestrator = None


def get_orchestrator() -> SystemOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        from .websocket import ws_manager
        _orchestrator = SystemOrchestrator(ws_manager)
    return _orchestrator