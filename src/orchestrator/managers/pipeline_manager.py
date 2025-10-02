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
    # Removed: analyze_and_fix_pipeline_failures() - Agents use MCP tools directly
    # Removed: check_pipeline_status() - Agents use MCP tools directly
    # Removed: get_latest_pipeline_status() - Agents use MCP tools directly
    # Removed: wait_for_pipeline_smart() - Agents use MCP tools directly
    # Users provide their own .gitlab-ci.yml pipelines
    # Agents use MCP tools (get_pipeline, get_pipeline_jobs, get_job_trace) directly