"""
Pipeline monitoring and waiting utilities for agents.
Ensures agents properly wait for pipeline completion before proceeding.
"""

import asyncio
import time
from typing import Dict, Any, Optional, Tuple
from ..utils import CompletionMarkers


class PipelineMonitor:
    """
    Centralized pipeline monitoring for agents.
    Ensures agents wait for pipeline completion before proceeding.
    """

    def __init__(self, tools: list, project_id: str):
        self.tools = tools
        self.project_id = project_id
        self.pipeline_tool = None
        self.pipeline_jobs_tool = None
        self.job_trace_tool = None
        self.cancel_pipeline_tool = None
        self.get_pipeline_tool = None

        # Track current pipeline being monitored
        self.current_pipeline_id = None
        self.monitored_pipelines = set()  # Track all pipelines we've monitored

        # Simple agent-pipeline tracking (KEY FIX)
        self.agent_pipelines = {}  # {agent_name: pipeline_id} - tracks which pipeline belongs to which agent

        # Initialize pipeline tools
        self._init_tools()

    def _init_tools(self):
        """Initialize GitLab pipeline tools."""
        for tool in self.tools:
            if hasattr(tool, 'name'):
                if tool.name == 'get_latest_pipeline_for_ref':
                    self.pipeline_tool = tool
                elif tool.name == 'get_pipeline_jobs':
                    self.pipeline_jobs_tool = tool
                elif tool.name == 'get_job_trace':
                    self.job_trace_tool = tool
                elif tool.name == 'cancel_pipeline':
                    self.cancel_pipeline_tool = tool
                elif tool.name == 'get_pipeline':
                    self.get_pipeline_tool = tool

    async def wait_for_pipeline_completion(
        self,
        branch: str,
        timeout_minutes: int = 20,  # Increased default timeout
        check_interval_seconds: int = 30,
        specific_pipeline_id: Optional[str] = None,  # Allow tracking specific pipeline
        agent_name: Optional[str] = None  # Track which agent is waiting
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Wait for pipeline completion on specified branch.

        Args:
            branch: Branch name to monitor
            timeout_minutes: Maximum time to wait
            check_interval_seconds: How often to check pipeline status
            specific_pipeline_id: Optional specific pipeline ID to monitor

        Returns:
            Tuple of (success, status_message, pipeline_summary)
        """
        if specific_pipeline_id:
            print(f"[PIPELINE MONITOR] Monitoring SPECIFIC pipeline #{specific_pipeline_id}")
        else:
            print(f"[PIPELINE MONITOR] Starting pipeline monitoring for branch: {branch}")
        print(f"[PIPELINE MONITOR] Timeout: {timeout_minutes} minutes, Check interval: {check_interval_seconds}s")

        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        last_status = None

        while True:
            elapsed = time.time() - start_time
            remaining = timeout_seconds - elapsed

            if elapsed >= timeout_seconds:
                return False, f"PIPELINE_TIMEOUT: No pipeline completed within {timeout_minutes} minutes", {}

            try:
                # Get latest pipeline for branch
                pipeline_info = await self._get_latest_pipeline(branch)

                if not pipeline_info:
                    print(f"[PIPELINE MONITOR] ⏳ No pipeline found yet (waiting {remaining/60:.1f} min remaining)")
                    await asyncio.sleep(check_interval_seconds)
                    continue

                pipeline_id = pipeline_info.get('id')
                status = pipeline_info.get('status', 'unknown')
                web_url = pipeline_info.get('web_url', 'N/A')

                # Register pipeline for agent if first time seeing it
                if agent_name and not self.get_agent_pipeline(agent_name):
                    self.register_agent_pipeline(agent_name, pipeline_id)

                # Validate if agent is monitoring correct pipeline
                if agent_name and not self.validate_agent_pipeline(agent_name, pipeline_id):
                    print(f"[PIPELINE MONITOR] ❌ Wrong pipeline! Agent {agent_name} should not use #{pipeline_id}")
                    # Continue to find the right pipeline
                    await asyncio.sleep(check_interval_seconds)
                    continue

                # Only print status changes to avoid spam
                if status != last_status:
                    print(f"[PIPELINE MONITOR] Pipeline #{pipeline_id} status: {status}")
                    print(f"[PIPELINE MONITOR] Pipeline URL: {web_url}")
                    last_status = status

                # Check if pipeline is still running
                if status in ['pending', 'running', 'created']:
                    print(f"[PIPELINE MONITOR] ⏳ Pipeline still {status}, waiting... ({remaining/60:.1f} min remaining)")
                    await asyncio.sleep(check_interval_seconds)
                    continue

                # Pipeline completed - analyze results
                print(f"[PIPELINE MONITOR] Pipeline completed with status: {status}")

                if status == 'success':
                    # Verify pipeline actually ran tests
                    success, summary = await self._verify_pipeline_success(pipeline_id)
                    if success:
                        return True, f"PIPELINE_SUCCESS: Pipeline #{pipeline_id} completed successfully", summary
                    else:
                        return False, f"PIPELINE_FAILED_VALIDATION: Pipeline #{pipeline_id} marked success but tests didn't run properly", summary

                elif status == 'failed':
                    # Analyze failure
                    failure_analysis = await self._analyze_pipeline_failure(pipeline_id)
                    return False, f"PIPELINE_FAILED: {failure_analysis['type']} - {failure_analysis['message']}", failure_analysis

                elif status == 'canceled':
                    return False, f"PIPELINE_CANCELED: Pipeline #{pipeline_id} was canceled", {}

                elif status == 'skipped':
                    return False, f"PIPELINE_SKIPPED: Pipeline #{pipeline_id} was skipped", {}

                else:
                    return False, f"PIPELINE_UNKNOWN: Pipeline #{pipeline_id} has unknown status: {status}", {}

            except Exception as e:
                print(f"[PIPELINE MONITOR] ⚠️ Error checking pipeline: {e}")
                await asyncio.sleep(check_interval_seconds)
                continue

    async def _get_latest_pipeline(self, branch: str) -> Optional[Dict[str, Any]]:
        """Get the latest pipeline for a branch."""
        if not self.pipeline_tool:
            return None

        try:
            response = await self.pipeline_tool.ainvoke({
                "project_id": self.project_id,
                "ref": branch
            })

            if isinstance(response, str):
                import json
                return json.loads(response)
            return response

        except Exception as e:
            print(f"[PIPELINE MONITOR] ⚠️ Error getting pipeline: {e}")
            return None

    async def _verify_pipeline_success(self, pipeline_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Verify that a 'successful' pipeline actually ran tests."""
        try:
            # Get all jobs for this pipeline
            jobs = await self._get_pipeline_jobs(pipeline_id)
            if not jobs:
                return False, {"error": "No jobs found"}

            summary = {
                "pipeline_id": pipeline_id,
                "jobs": [],
                "tests_ran": False,
                "build_succeeded": False,
                "artifacts_created": False
            }

            for job in jobs:
                job_name = job.get('name', 'unknown')
                job_status = job.get('status', 'unknown')
                job_id = job.get('id')

                job_info = {
                    "name": job_name,
                    "status": job_status,
                    "id": job_id
                }

                # Get job trace to verify what actually happened
                if job_status == 'success' and job_name in ['test_job', 'test']:
                    trace = await self._get_job_trace(job_id)
                    if trace:
                        # Use our completion markers to check if tests actually ran
                        tests_actually_ran = CompletionMarkers.tests_actually_ran(trace)
                        pipeline_summary = CompletionMarkers.get_pipeline_summary(trace)

                        job_info.update({
                            "tests_ran": tests_actually_ran,
                            "trace_summary": pipeline_summary
                        })

                        if tests_actually_ran:
                            summary["tests_ran"] = True
                            summary["artifacts_created"] = pipeline_summary.get("artifacts_uploaded", False)

                elif job_status == 'success' and job_name in ['build_job', 'build']:
                    summary["build_succeeded"] = True

                summary["jobs"].append(job_info)

            # Pipeline is only truly successful if tests actually ran
            overall_success = summary["tests_ran"] and summary["build_succeeded"]

            return overall_success, summary

        except Exception as e:
            return False, {"error": f"Pipeline verification failed: {e}"}

    async def _analyze_pipeline_failure(self, pipeline_id: str) -> Dict[str, Any]:
        """Analyze why a pipeline failed."""
        try:
            jobs = await self._get_pipeline_jobs(pipeline_id)
            if not jobs:
                return {"type": "UNKNOWN", "message": "No job information available"}

            failed_jobs = [job for job in jobs if job.get('status') == 'failed']

            if not failed_jobs:
                return {"type": "UNKNOWN", "message": "Pipeline failed but no failed jobs found"}

            # Analyze the first failed job
            failed_job = failed_jobs[0]
            job_name = failed_job.get('name', 'unknown')
            job_id = failed_job.get('id')

            # Get job trace to understand the failure
            trace = await self._get_job_trace(job_id)
            if not trace:
                return {"type": "TRACE_UNAVAILABLE", "message": f"Failed job {job_name} but trace unavailable"}

            # Categorize failure type
            trace_lower = trace.lower()

            if any(indicator in trace_lower for indicator in ["could not resolve", "failed to read artifact", "build failure"]):
                return {
                    "type": "DEPENDENCY_FAILURE",
                    "message": f"Maven dependency resolution failed in {job_name}",
                    "job": job_name,
                    "trace_excerpt": trace[-500:]  # Last 500 chars of trace
                }

            elif "test" in job_name.lower():
                return {
                    "type": "TEST_FAILURE",
                    "message": f"Tests failed in {job_name}",
                    "job": job_name,
                    "trace_excerpt": trace[-500:]
                }

            elif "build" in job_name.lower():
                return {
                    "type": "BUILD_FAILURE",
                    "message": f"Build failed in {job_name}",
                    "job": job_name,
                    "trace_excerpt": trace[-500:]
                }

            else:
                return {
                    "type": "GENERAL_FAILURE",
                    "message": f"Job {job_name} failed",
                    "job": job_name,
                    "trace_excerpt": trace[-500:]
                }

        except Exception as e:
            return {"type": "ANALYSIS_ERROR", "message": f"Failed to analyze pipeline failure: {e}"}

    async def _get_pipeline_jobs(self, pipeline_id: str) -> list:
        """Get jobs for a pipeline."""
        if not self.pipeline_jobs_tool:
            return []

        try:
            response = await self.pipeline_jobs_tool.ainvoke({
                "project_id": self.project_id,
                "pipeline_id": str(pipeline_id)
            })

            if isinstance(response, str):
                import json
                return json.loads(response)
            return response or []

        except Exception as e:
            print(f"[PIPELINE MONITOR] ⚠️ Error getting pipeline jobs: {e}")
            return []

    async def _get_job_trace(self, job_id: str) -> Optional[str]:
        """Get trace for a specific job."""
        if not self.job_trace_tool:
            return None

        try:
            response = await self.job_trace_tool.ainvoke({
                "project_id": self.project_id,
                "job_id": str(job_id)
            })

            if isinstance(response, str):
                return response
            return str(response) if response else None

        except Exception as e:
            print(f"[PIPELINE MONITOR] ⚠️ Error getting job trace: {e}")
            return None

    async def cancel_old_pipelines(self, branch: str, keep_pipeline_id: Optional[str] = None):
        """
        Cancel all old pipelines for a branch except the specified one.

        Args:
            branch: Branch name
            keep_pipeline_id: Pipeline ID to keep running (all others will be canceled)
        """
        print(f"[PIPELINE MONITOR] Canceling old pipelines for branch: {branch}")

        try:
            # Get all pipelines for the branch
            if not self.pipeline_tool:
                return

            # Get recent pipelines (usually returns latest, but let's be thorough)
            response = await self.pipeline_tool.ainvoke({
                "project_id": self.project_id,
                "ref": branch
            })

            if isinstance(response, str):
                import json
                pipelines = [json.loads(response)]
            elif isinstance(response, list):
                pipelines = response
            elif isinstance(response, dict):
                pipelines = [response]
            else:
                pipelines = []

            # Cancel all pipelines except the one we want to keep
            canceled_count = 0
            for pipeline in pipelines:
                pipeline_id = str(pipeline.get('id'))
                status = pipeline.get('status', '')

                # Skip if this is the pipeline we want to keep
                if keep_pipeline_id and pipeline_id == str(keep_pipeline_id):
                    print(f"[PIPELINE MONITOR] ✅ Keeping pipeline #{pipeline_id}")
                    continue

                # Cancel if it's still running
                if status in ['pending', 'running', 'created']:
                    if self.cancel_pipeline_tool:
                        try:
                            await self.cancel_pipeline_tool.ainvoke({
                                "project_id": self.project_id,
                                "pipeline_id": pipeline_id
                            })
                            canceled_count += 1
                            print(f"[PIPELINE MONITOR] ❌ Canceled old pipeline #{pipeline_id}")
                        except Exception as e:
                            print(f"[PIPELINE MONITOR] ⚠️ Failed to cancel pipeline #{pipeline_id}: {e}")

            if canceled_count > 0:
                print(f"[PIPELINE MONITOR] Canceled {canceled_count} old pipeline(s)")
            else:
                print(f"[PIPELINE MONITOR] ✅ No old pipelines to cancel")

        except Exception as e:
            print(f"[PIPELINE MONITOR] ⚠️ Error canceling old pipelines: {e}")

    def set_current_pipeline(self, pipeline_id: str):
        """
        Set the current pipeline ID being monitored.
        This helps agents track which pipeline is theirs.
        """
        self.current_pipeline_id = str(pipeline_id)
        self.monitored_pipelines.add(str(pipeline_id))
        print(f"[PIPELINE MONITOR] Now monitoring pipeline #{pipeline_id}")

    def get_current_pipeline(self) -> Optional[str]:
        """Get the current pipeline ID being monitored."""
        return self.current_pipeline_id

    def is_my_pipeline(self, pipeline_id: str) -> bool:
        """Check if a pipeline ID is the one we're currently monitoring."""
        return str(pipeline_id) == str(self.current_pipeline_id)

    def register_agent_pipeline(self, agent_name: str, pipeline_id: str) -> None:
        """
        Register a pipeline as belonging to a specific agent.
        This is the KEY to preventing pipeline confusion.

        Args:
            agent_name: Name of the agent (e.g., 'testing', 'review')
            pipeline_id: The pipeline ID created by this agent
        """
        self.agent_pipelines[agent_name] = str(pipeline_id)
        print(f"[PIPELINE TRACKING] Registered pipeline #{pipeline_id} for {agent_name} agent")

    def get_agent_pipeline(self, agent_name: str) -> Optional[str]:
        """
        Get the pipeline ID that belongs to a specific agent.

        Args:
            agent_name: Name of the agent

        Returns:
            Pipeline ID or None if not registered
        """
        return self.agent_pipelines.get(agent_name)

    def validate_agent_pipeline(self, agent_name: str, pipeline_id: str) -> bool:
        """
        Validate that an agent is using the correct pipeline.

        Args:
            agent_name: Name of the agent
            pipeline_id: Pipeline ID the agent is trying to use

        Returns:
            True if this is the correct pipeline for the agent
        """
        correct_pipeline = self.agent_pipelines.get(agent_name)
        if correct_pipeline and str(pipeline_id) != str(correct_pipeline):
            print(f"[PIPELINE WARNING] {agent_name} agent trying to use pipeline #{pipeline_id} but owns #{correct_pipeline}")
            return False
        return True