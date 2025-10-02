"""
Pipeline Management Module
Handles CI/CD pipeline operations including creation, monitoring, and failure analysis.
"""

import json
from typing import Dict, List, Optional, Any
from ..pipeline import PipelineConfig


class PipelineManager:
    """
    Manages CI/CD pipeline operations including configuration, monitoring, and debugging.
    """

    def __init__(self, project_id: str, tools: List[Any], default_branch: str = "master"):
        self.project_id = project_id
        self.tools = tools
        self.default_branch = default_branch
        self.pipeline_config = None

        # Pipeline optimization settings
        self.MAX_PENDING_TIME = 120  # 2 minutes max for pending state only
        self.MAX_RUNNING_TIME = 600  # 10 minutes max for running state (actual execution)
        self.CHECK_INTERVAL = 10  # Check every 10 seconds instead of 30

    def _normalize_tech_stack(self, tech_stack: Dict[str, str]) -> Dict[str, str]:
        """
        Normalize tech stack format from Web GUI to PipelineConfig format.
        Web GUI format: {'language': 'Java', 'framework': None, 'min_coverage': 70, ...}
        PipelineConfig format: {'backend': 'java', 'frontend': 'none', 'min_coverage': 70}
        """
        normalized = {}

        # Map 'language' to 'backend' and convert to lowercase
        if 'language' in tech_stack:
            language = tech_stack['language']
            if language:
                normalized['backend'] = language.lower()

        # Map framework/frontend
        if 'framework' in tech_stack:
            framework = tech_stack.get('framework')
            if framework and framework.lower() != 'none':
                normalized['frontend'] = framework.lower()
            else:
                normalized['frontend'] = 'none'

        # If backend wasn't set, check if it's already in the dict
        if 'backend' not in normalized and 'backend' in tech_stack:
            normalized['backend'] = tech_stack['backend'].lower()

        # Default to 'none' for frontend if not set
        if 'frontend' not in normalized:
            normalized['frontend'] = 'none'

        # Default to 'python' for backend if not set
        if 'backend' not in normalized:
            normalized['backend'] = 'python'

        # Preserve min_coverage if provided
        if 'min_coverage' in tech_stack:
            normalized['min_coverage'] = tech_stack['min_coverage']

        return normalized

    async def initialize_pipeline_config(self, tech_stack: Dict[str, str] = None, mode: str = 'minimal'):
        """
        Initialize pipeline configuration (tech stack only).
        Users provide their own .gitlab-ci.yml - no pipeline generation.

        Args:
            tech_stack: Technology stack configuration
            mode: Unused - kept for backward compatibility
        """
        try:
            # Use provided tech stack if available, otherwise detect from project files
            if tech_stack:
                print(f"[PIPELINE CONFIG] Using provided tech stack: {tech_stack}")
                # Convert Web GUI format to PipelineConfig format
                tech_stack = self._normalize_tech_stack(tech_stack)
            else:
                tech_stack = await self.detect_project_tech_stack()

            # Initialize pipeline config (stores tech stack only)
            self.pipeline_config = PipelineConfig(tech_stack, mode=mode)

            print(f"[PIPELINE CONFIG] Initialized for {tech_stack.get('backend', 'unknown')} backend")
            if tech_stack.get('frontend') != 'none':
                print(f"[PIPELINE CONFIG] Frontend: {tech_stack.get('frontend')}")

            # Note: Users provide their own .gitlab-ci.yml - no automatic pipeline creation

        except Exception as e:
            print(f"[PIPELINE CONFIG] Failed to initialize: {e}")
            # Use default Python config as fallback
            self.pipeline_config = PipelineConfig({'backend': 'python', 'frontend': 'none'}, mode=mode)

    async def detect_project_tech_stack(self) -> Dict[str, str]:
        """Detect project tech stack from repository files."""
        tech_stack = {'backend': 'unknown', 'frontend': 'none'}

        try:
            list_tree_tool = self._get_tool('list_tree')

            if list_tree_tool:
                tree = await list_tree_tool.ainvoke({
                    "project_id": self.project_id,
                    "path": "/",
                    "per_page": 100
                })

                # Analyze files to detect tech stack
                file_names = [item.get('name', '') for item in tree if item.get('type') == 'blob']

                # Backend detection
                if 'requirements.txt' in file_names or 'setup.py' in file_names or 'pyproject.toml' in file_names:
                    tech_stack['backend'] = 'python'
                elif 'package.json' in file_names:
                    tech_stack['backend'] = 'nodejs'
                elif 'pom.xml' in file_names:
                    tech_stack['backend'] = 'java'
                elif 'go.mod' in file_names:
                    tech_stack['backend'] = 'go'
                elif 'Cargo.toml' in file_names:
                    tech_stack['backend'] = 'rust'
                elif 'composer.json' in file_names:
                    tech_stack['backend'] = 'php'
                elif 'Gemfile' in file_names:
                    tech_stack['backend'] = 'ruby'

                # Frontend detection
                if 'index.html' in file_names:
                    tech_stack['frontend'] = 'html-css-js'

                # Check package.json for frontend frameworks if Node.js
                if 'package.json' in file_names:
                    read_file_tool = self._get_tool('read_file')

                    if read_file_tool:
                        try:
                            package_content = await read_file_tool.ainvoke({
                                "project_id": self.project_id,
                                "file_path": "package.json"
                            })

                            if 'react' in package_content.lower():
                                tech_stack['frontend'] = 'react'
                            elif 'vue' in package_content.lower():
                                tech_stack['frontend'] = 'vue'
                            elif 'angular' in package_content.lower():
                                tech_stack['frontend'] = 'angular'
                        except:
                            pass

            # Fallback to Python if nothing detected
            if tech_stack['backend'] == 'unknown':
                tech_stack['backend'] = 'python'
                print("[PIPELINE CONFIG] No tech stack detected, defaulting to Python")

        except Exception as e:
            print(f"[PIPELINE CONFIG] Tech stack detection failed: {e}")
            tech_stack = {'backend': 'python', 'frontend': 'none'}

        return tech_stack

    # Removed: ensure_basic_pipeline_exists()
    # Removed: get_pipeline_instructions()
    # Users provide their own .gitlab-ci.yml pipelines

    async def analyze_and_fix_pipeline_failures(self, issue_id: str, executor) -> Dict[str, Any]:
        """
        Analyze CI/CD pipeline failures and provide debugging guidance.
        Returns debugging context for agents.
        """
        debugging_context = {}
        try:
            # Get latest pipeline status
            pipeline_info = await self.get_latest_pipeline_status()
            if not pipeline_info:
                return debugging_context

            status = pipeline_info.get("status", "unknown")
            if status != "success":
                print(f"\n[PIPELINE] Issue #{issue_id} - Status: {status}")

                # Get failed job details
                output = pipeline_info.get("output", "")
                if "FAILED" in output or "ERROR" in output:
                    print(f"[PIPELINE] Tests or build failed - agents will need to debug")

                    # Store context for agents
                    debugging_context = {
                        "issue_id": issue_id,
                        "pipeline_status": status,
                        "output": output[:1000]  # First 1000 chars for context
                    }

                    # Set debugging context in executor if provided
                    if executor:
                        executor.debugging_context = debugging_context

        except Exception as e:
            print(f"[PIPELINE] Could not analyze pipeline: {e}")

        return debugging_context

    async def check_pipeline_status(self, issue_id: str):
        """
        Check pipeline status before finalizing implementation.
        """
        try:
            print(f"[PIPELINE] Checking status for issue #{issue_id}")

            # Get latest pipeline status
            pipeline_info = await self.get_latest_pipeline_status()
            if pipeline_info:
                status = pipeline_info.get("status", "unknown")

                if status == "success":
                    print(f"[PIPELINE] [OK] Pipeline passed - all tests green")
                elif status == "failed":
                    print(f"[PIPELINE] [FAIL] Pipeline failed - review needed")
                elif status == "running":
                    print(f"[PIPELINE] Pipeline still running")
                else:
                    print(f"[PIPELINE] Status: {status}")

        except Exception as e:
            print(f"[PIPELINE] Check failed: {e}")

    async def get_latest_pipeline_status(self) -> Optional[Dict]:
        """
        Get the latest CI/CD pipeline status and output.
        """
        try:
            get_pipelines_tool = self._get_tool('get_pipelines')

            if not get_pipelines_tool:
                return None

            # Get latest pipeline
            pipelines = await get_pipelines_tool.ainvoke({
                "project_id": self.project_id,
                "per_page": 1
            })

            if pipelines and len(pipelines) > 0:
                pipeline = pipelines[0]
                pipeline_id = pipeline.get("id")

                # Get pipeline jobs
                get_jobs_tool = self._get_tool('get_pipeline_jobs')

                if get_jobs_tool:
                    jobs = await get_jobs_tool.ainvoke({
                        "project_id": self.project_id,
                        "pipeline_id": pipeline_id
                    })

                    # Get job traces for failed jobs
                    output_parts = []
                    for job in jobs:
                        if job.get("status") in ["failed", "success"]:
                            # Get job trace
                            get_trace_tool = self._get_tool('get_job_trace')

                            if get_trace_tool:
                                trace = await get_trace_tool.ainvoke({
                                    "project_id": self.project_id,
                                    "job_id": job.get("id")
                                })
                                output_parts.append(trace)

                    return {
                        "pipeline_id": pipeline_id,
                        "status": pipeline.get("status"),
                        "output": "\n".join(output_parts)
                    }

        except Exception as e:
            print(f"[PIPELINE] Could not fetch status: {e}")

        return None

    def _get_tool(self, tool_name: str):
        """Helper to get a tool by name."""
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
        return None

    async def cancel_obsolete_pipelines(self, branch: str = None, keep_latest: int = 1):
        """
        Cancel obsolete pipelines to prevent queue buildup.
        Keeps only the latest pipeline(s) running.
        """
        try:
            get_pipelines_tool = self._get_tool('get_pipelines')
            cancel_pipeline_tool = self._get_tool('cancel_pipeline')

            if not get_pipelines_tool:
                return

            params = {"project_id": self.project_id, "per_page": 20}
            if branch:
                params["ref"] = branch

            pipelines = await get_pipelines_tool.ainvoke(params)

            # Skip the most recent pipelines
            pipelines_to_cancel = pipelines[keep_latest:] if len(pipelines) > keep_latest else []

            canceled_count = 0
            for pipeline in pipelines_to_cancel:
                status = pipeline.get("status", "")
                if status in ["pending", "running", "created"]:
                    pipeline_id = pipeline.get("id")

                    if cancel_pipeline_tool:
                        try:
                            await cancel_pipeline_tool.ainvoke({
                                "project_id": self.project_id,
                                "pipeline_id": pipeline_id
                            })
                            canceled_count += 1
                            print(f"[PIPELINE] Canceled obsolete pipeline #{pipeline_id}")
                        except:
                            pass

            if canceled_count > 0:
                print(f"[PIPELINE] Canceled {canceled_count} obsolete pipelines")

        except Exception as e:
            print(f"[PIPELINE] Failed to cancel pipelines: {e}")

    async def wait_for_pipeline_smart(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Smart pipeline waiting with state-specific timeouts.
        - Pending state: 2 minute timeout (if runners are unavailable)
        - Running state: 10 minute timeout (actual execution time)
        """
        import asyncio
        from datetime import datetime

        start_time = datetime.now()
        last_status = None
        pending_start_time = None
        running_start_time = None

        get_pipeline_tool = self._get_tool('get_single_pipeline')
        get_jobs_tool = self._get_tool('get_pipeline_jobs')

        if not get_pipeline_tool:
            return {"status": "error", "message": "Pipeline tools not available"}

        while True:
            elapsed_total = (datetime.now() - start_time).total_seconds()

            try:
                # Get current pipeline status
                pipeline = await get_pipeline_tool.ainvoke({
                    "project_id": self.project_id,
                    "pipeline_id": pipeline_id
                })

                status = pipeline.get("status", "unknown")

                # Track state transitions
                if status != last_status:
                    print(f"[PIPELINE] Pipeline #{pipeline_id}: {status}")

                    if status == "pending" and pending_start_time is None:
                        pending_start_time = datetime.now()
                        print(f"[PIPELINE] Pipeline entered pending state (max {self.MAX_PENDING_TIME}s)")

                    elif status == "running":
                        if running_start_time is None:
                            running_start_time = datetime.now()
                            print(f"[PIPELINE] Pipeline started running (max {self.MAX_RUNNING_TIME}s)")
                        pending_start_time = None  # Reset pending timer

                    last_status = status

                # Check if complete
                if status in ["success", "failed", "canceled", "skipped"]:
                    return {"status": status, "pipeline": pipeline}

                # State-specific timeout checks
                if status == "pending" and pending_start_time:
                    pending_duration = (datetime.now() - pending_start_time).total_seconds()
                    if pending_duration > self.MAX_PENDING_TIME:
                        print(f"[PIPELINE] Pending timeout after {pending_duration:.0f}s - no runners available")
                        return {
                            "status": "timeout_pending",
                            "message": f"Pipeline stuck in pending state for {pending_duration:.0f}s",
                            "recommendation": "GitLab runners may be unavailable or busy"
                        }

                elif status == "running" and running_start_time:
                    running_duration = (datetime.now() - running_start_time).total_seconds()
                    if running_duration > self.MAX_RUNNING_TIME:
                        print(f"[PIPELINE] Running timeout after {running_duration:.0f}s")
                        return {
                            "status": "timeout_running",
                            "message": f"Pipeline exceeded maximum execution time ({running_duration:.0f}s)",
                            "recommendation": "Tests may be hanging or taking too long"
                        }

                # Check for stuck jobs in pending state
                if status == "pending" and get_jobs_tool:
                    jobs = await get_jobs_tool.ainvoke({
                        "project_id": self.project_id,
                        "pipeline_id": pipeline_id
                    })

                    running_jobs = [j for j in jobs if j.get("status") == "running"]
                    if running_jobs:
                        print(f"[PIPELINE] {len(running_jobs)} jobs running despite 'pending' status")
                        # Pipeline status may be cached, continue waiting

            except Exception as e:
                print(f"[PIPELINE] Error checking pipeline: {e}")

            # Wait before next check
            await asyncio.sleep(self.CHECK_INTERVAL)

    async def wait_for_pipeline(self, pipeline_id: str, timeout: int = None) -> Dict[str, Any]:
        """
        Backward compatible wait method with smart timeout handling.
        """
        return await self.wait_for_pipeline_smart(pipeline_id)