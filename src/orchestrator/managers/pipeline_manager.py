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

    async def initialize_pipeline_config(self, tech_stack: Dict[str, str] = None):
        """Initialize pipeline configuration and create basic pipeline if needed."""
        try:
            # Use provided tech stack if available, otherwise detect from project files
            if tech_stack:
                print(f"[PIPELINE CONFIG] Using provided tech stack: {tech_stack}")
            else:
                tech_stack = await self.detect_project_tech_stack()

            # Initialize pipeline config
            self.pipeline_config = PipelineConfig(tech_stack)

            print(f"[PIPELINE CONFIG] Initialized for {tech_stack.get('backend', 'unknown')} backend")
            if tech_stack.get('frontend') != 'none':
                print(f"[PIPELINE CONFIG] Frontend: {tech_stack.get('frontend')}")

            # Create basic pipeline if it doesn't exist
            await self.ensure_basic_pipeline_exists()

        except Exception as e:
            print(f"[PIPELINE CONFIG] Failed to initialize: {e}")
            # Use default Python config as fallback
            self.pipeline_config = PipelineConfig({'backend': 'python', 'frontend': 'none'})

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

    async def ensure_basic_pipeline_exists(self):
        """Create a basic .gitlab-ci.yml pipeline if it doesn't exist."""
        try:
            get_file_tool = self._get_tool('get_file_contents')

            if not get_file_tool:
                print("[PIPELINE] get_file_contents tool not found - cannot check for existing pipeline")
                return

            # Try to get existing pipeline
            try:
                existing_pipeline = await get_file_tool.ainvoke({
                    "project_id": self.project_id,
                    "file_path": ".gitlab-ci.yml",
                    "ref": self.default_branch
                })

                if existing_pipeline:
                    print("[PIPELINE] ✅ Basic pipeline already exists - skipping creation")
                    return

            except Exception:
                # File doesn't exist, that's fine - we'll create it
                pass

            # Generate basic pipeline content
            pipeline_yaml = self.pipeline_config.generate_pipeline_yaml()

            # Create the pipeline file
            create_file_tool = self._get_tool('create_or_update_file')

            if not create_file_tool:
                print("[PIPELINE] create_or_update_file tool not found - cannot create pipeline")
                return

            await create_file_tool.ainvoke({
                "project_id": self.project_id,
                "file_path": ".gitlab-ci.yml",
                "content": pipeline_yaml,
                "commit_message": f"feat: add basic CI/CD pipeline for {self.pipeline_config.backend}",
                "branch": self.default_branch
            })

            print(f"[PIPELINE] ✅ Created basic {self.pipeline_config.backend} pipeline (.gitlab-ci.yml)")

        except Exception as e:
            print(f"[PIPELINE] ⚠️ Failed to create basic pipeline: {e}")
            print("[PIPELINE] Project will continue without CI/CD pipeline")

    def get_pipeline_instructions(self) -> str:
        """Get dynamic pipeline instructions for agents."""
        if not self.pipeline_config:
            return "Use standard Python pipeline with pytest"

        config = self.pipeline_config.config
        instructions = []

        instructions.append(f"PIPELINE CONFIGURATION FOR {config.get('backend', 'python').upper()}:")
        instructions.append(f"- Docker Image: {config.get('docker_image', 'python:3.11-slim')}")
        instructions.append(f"- Test Framework: {config.get('test_framework', 'pytest')}")
        instructions.append(f"- Package Manager: {config.get('package_manager', 'pip')}")
        instructions.append(f"- Requirements File: {config.get('requirements_file', 'requirements.txt')}")
        instructions.append(f"- Test Directory: {config.get('test_directory', 'tests')}")
        instructions.append(f"- Source Directory: {config.get('source_directory', 'src')}")
        instructions.append(f"- Min Coverage: {config.get('min_coverage', 70)}%")
        instructions.append("")
        instructions.append("TEST COMMAND:")
        instructions.append(f"  {self.pipeline_config.get_test_command()}")
        instructions.append("")
        instructions.append("COVERAGE COMMAND:")
        instructions.append(f"  {self.pipeline_config.get_coverage_command()}")

        return '\n'.join(instructions)

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
                    print(f"[PIPELINE] ✅ Pipeline passed - all tests green")
                elif status == "failed":
                    print(f"[PIPELINE] ❌ Pipeline failed - review needed")
                elif status == "running":
                    print(f"[PIPELINE] 🔄 Pipeline still running")
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