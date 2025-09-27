"""
Supervisor Orchestrator - Enhanced with robust issue handling and recovery
Main orchestrator that coordinates specialized modules for workflow management.
Handles MCP server integration and proper agent instruction flow.
"""

import asyncio
import json
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime
from enum import Enum

from ..infrastructure.mcp_client import get_common_tools_and_client, SafeMCPClient

# Import core components
from .core import PerformanceTracker, Router, AgentExecutor
from .pipeline import PipelineConfig


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
    Enhanced orchestrator with robust issue handling and MCP integration.
    Properly manages agent dependencies and instruction flow.
    """
    
    def __init__(self, project_id: str, tech_stack: dict = None):
        self.project_id = project_id
        self.tools = None
        self.client = None
        self.default_branch = "master"
        self.current_plan = None
        self.state = ExecutionState.INITIALIZING
        self.provided_tech_stack = tech_stack  # Store user-provided tech stack

        # Issue tracking
        self.gitlab_issues = []
        self.implementation_queue = []
        self.completed_issues = []
        self.failed_issues = []

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 5

        # Initialize core components
        self.router = Router()
        self.executor = AgentExecutor(project_id, [])
        self.performance_tracker = PerformanceTracker()
        self.min_coverage = 70.0  # Minimum test coverage requirement
        self.pipeline_config = None  # Will be initialized after tech stack detection

        # Checkpoint system removed - was incomplete
    
    def _validate_issue(self, issue: Dict) -> bool:
        """Simple issue validation - replaces entire validation module."""
        if not isinstance(issue, dict):
            print(f"[VALIDATION] Issue must be a dictionary")
            return False
        if "iid" not in issue or "title" not in issue:
            print(f"[VALIDATION] Issue missing required fields (iid or title)")
            return False
        return True
    
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
            print(f"[MODULES] Router, Executor, Performance tracker loaded")
            
            # Fetch project info to get actual default branch
            await self._fetch_project_info()
            
            # Initialize pipeline configuration based on tech stack
            await self._initialize_pipeline_config()
            
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
    
    async def _initialize_pipeline_config(self):
        """Initialize pipeline configuration and create basic pipeline if needed."""
        try:
            # Use provided tech stack if available, otherwise detect from project files
            if self.provided_tech_stack:
                tech_stack = self.provided_tech_stack
                print(f"[PIPELINE CONFIG] Using provided tech stack: {tech_stack}")
            else:
                tech_stack = await self._detect_project_tech_stack()

            # Initialize pipeline config
            self.pipeline_config = PipelineConfig(tech_stack)

            print(f"[PIPELINE CONFIG] Initialized for {tech_stack.get('backend', 'unknown')} backend")
            if tech_stack.get('frontend') != 'none':
                print(f"[PIPELINE CONFIG] Frontend: {tech_stack.get('frontend')}")

            # Store config in executor for agents to use
            self.executor.pipeline_config = self.pipeline_config

            # Create basic pipeline if it doesn't exist
            await self._ensure_basic_pipeline_exists()

        except Exception as e:
            print(f"[PIPELINE CONFIG] Failed to initialize: {e}")
            # Use default Python config as fallback
            self.pipeline_config = PipelineConfig({'backend': 'python', 'frontend': 'none'})
    
    async def _detect_project_tech_stack(self) -> Dict[str, str]:
        """Detect project tech stack from repository files."""
        tech_stack = {'backend': 'unknown', 'frontend': 'none'}
        
        try:
            # Use list_tree to examine project structure
            list_tree_tool = None
            for tool in self.tools:
                if hasattr(tool, 'name') and tool.name == 'list_tree':
                    list_tree_tool = tool
                    break
            
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
                    # Try to read package.json
                    read_file_tool = None
                    for tool in self.tools:
                        if hasattr(tool, 'name') and tool.name == 'read_file':
                            read_file_tool = tool
                            break
                    
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

    async def _ensure_basic_pipeline_exists(self):
        """Create a basic .gitlab-ci.yml pipeline if it doesn't exist."""
        try:
            # Check if pipeline already exists
            get_file_tool = None
            for tool in self.tools:
                if hasattr(tool, 'name') and tool.name == 'get_file_contents':
                    get_file_tool = tool
                    break

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
            create_file_tool = None
            for tool in self.tools:
                if hasattr(tool, 'name') and tool.name == 'create_or_update_file':
                    create_file_tool = tool
                    break

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
            print(f"[ERROR] {routing_result['agent']}: {e}")
            
            print(f"[SUPERVISOR] ❌ Agent coordination failed: {e}")
            raise Exception(f"Task {task_type} failed: {e}")
    
    async def implement_issue(self, issue: Dict, max_retries: int = None) -> bool:
        """
        Implement a single issue with optional retry logic.
        """
        issue_id = issue.get("iid")
        issue_title = issue.get("title", "Unknown")
        retries = max_retries if max_retries is not None else self.max_retries

        # Validate issue structure
        if not self._validate_issue(issue):
            print(f"[ERROR] Invalid issue structure for #{issue_id}")
            return False

        # Retry loop
        for attempt in range(retries):
            if attempt > 0:
                print(f"[RETRY] Issue #{issue_id} attempt {attempt + 1}/{retries}")
                await asyncio.sleep(self.retry_delay * attempt)

            print(f"\n[ISSUE #{issue_id}] Starting: {issue_title}")
            print(f"[ISSUE #{issue_id}] Implementation starting")

            # Implement issue through agent pipeline
            try:
                # Create feature branch name for this issue
                import re
                issue_title = issue.get('title', '')
                # Clean the title: remove special chars, replace spaces with hyphens
                issue_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', issue_title).lower()
                issue_slug = re.sub(r'\s+', '-', issue_slug).strip('-')[:30]
                feature_branch = f"feature/issue-{issue_id}-{issue_slug}"

                # Phase 1: Coding with pipeline config
                print(f"[ISSUE #{issue_id}] Phase 1/3: Coding...")
                print(f"[ISSUE #{issue_id}] Working on branch: {feature_branch}")
                coding_result = await self.route_task(
                "coding",
                issue=issue,
                branch=feature_branch
                )

                if not coding_result:
                    print(f"[ISSUE #{issue_id}] ❌ Coding phase failed")
                    continue  # Retry the whole issue

                # Phase 2: Testing with quality validation
                print(f"[ISSUE #{issue_id}] Phase 2/3: Testing...")

                # Log testing phase
                print(f"[ISSUE #{issue_id}] Running tests with minimum {self.min_coverage}% coverage requirement")

                testing_result = await self.route_task(
                "testing",
                issue=issue,
                branch=feature_branch  # Use the same feature branch
                )

                if not testing_result:
                    print(f"[ISSUE #{issue_id}] ⚠️ Testing phase failed")
                    # Check pipeline for debugging info
                    await self._analyze_and_fix_pipeline_failures(issue_id)

                # Phase 3: Review & Merge Request with quality check
                print(f"[ISSUE #{issue_id}] Phase 3/3: Review & MR...")

                # Check pipeline status before review
                await self._check_pipeline_status(issue_id)

                review_result = await self.route_task(
                "review",
                issue=issue,
                branch=feature_branch  # Use the same feature branch
                )

                if review_result:
                    print(f"[ISSUE #{issue_id}] ✅ Successfully implemented")
                    await self._update_orchestration_plan_for_completed_issue(issue)
                    return True  # Success!

            except Exception as e:
                print(f"[ISSUE #{issue_id}] ❌ Implementation failed: {e}")
                if attempt < retries - 1:
                    continue  # Retry
                return False  # Final failure
        # If we get here, all retries failed
        return False
    
    async def execute(self, mode: str = "implement", specific_issue: str = None, resume: bool = False):
        """
        Enhanced execution with state management and robust error handling.
        Properly handles MCP server integration and agent instruction flow.
        """
        print(f"\n{'='*70}")
        print(f"🚀 GITLAB AGENT SYSTEM - ENHANCED ORCHESTRATION")
        print(f"{'='*70}")
        print(f"Project: {self.project_id}")
        print(f"Mode: {mode}")
        print(f"State: {self.state.value}")
        
        # Resume functionality removed - was incomplete
        if resume:
            print("[WARNING] Resume functionality is not currently implemented")
        
        # Initialize with validation
        try:
            self.state = ExecutionState.INITIALIZING
            await self.initialize()
        except Exception as e:
            print(f"[SUPERVISOR] ❌ Initialization failed: {e}")
            print(f"[ERROR] Initialization: {e}")
            self.state = ExecutionState.FAILED
            return
        
        # Phase 1: Planning (always run to get context)
        self.state = ExecutionState.PLANNING
        print("\n" + "="*60)
        print("PHASE 1: PLANNING & ANALYSIS")
        print("="*60)
        
        apply_changes = mode in ["implement", "single"]
        
        # Run planning analysis (no plan file needed)
        success = await self._execute_planning_with_retry(apply_changes)
        if not success:
            print("[ERROR] Planning analysis failed after retries")
            print("[ERROR] Planning phase failed")
            self.state = ExecutionState.FAILED
            return

        # Store the planning result for later use
        if hasattr(self.executor, 'current_plan') and self.executor.current_plan:
            self.current_plan = self.executor.current_plan
            print("[PLANNING] Stored planning result for issue prioritization")
        
        if mode == "analyze":
            print("\n[COMPLETE] Analysis done. Run with --apply to implement.")
            self.state = ExecutionState.COMPLETED
            await self._show_summary()
            return
        
        # Phase 2: Implementation - Use planning agent's prioritization
        print("\n" + "="*60)
        print("PHASE 2: IMPLEMENTATION PREPARATION")
        print("="*60)

        # Fetch issues from GitLab and apply planning prioritization
        print("[ISSUES] Fetching issues from GitLab...")
        all_gitlab_issues = await self._fetch_gitlab_issues_via_mcp()

        if not all_gitlab_issues:
            print("[ISSUES] No open issues found")
            await self._show_summary()
            return

        print(f"[ISSUES] Found {len(all_gitlab_issues)} open issues from GitLab")

        # Apply planning agent's prioritization and filter completed issues
        issues = await self._apply_planning_prioritization(all_gitlab_issues)

        if issues:
            print(f"[ISSUES] After planning prioritization and filtering: {len(issues)} issues to implement")
            # Show issue details in priority order
            for issue in issues[:5]:  # Show first 5
                issue_id = issue.get('iid') or issue.get('id')
                title = issue.get('title', 'No title')
                print(f"  - Issue #{issue_id}: {title}")
        else:
            print("[ISSUES] No issues need implementation (all completed or merged)")
            await self._show_summary()
            return
        
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
                # All issues mode - issues already filtered by planning prioritization
                issues_to_implement = issues

                if not issues_to_implement:
                    print("[INFO] All issues are already completed")
                    await self._show_summary()
                    return
            
            print(f"[PLAN] Will implement {len(issues_to_implement)} issues")
            
            # Show issue titles for clarity
            for issue in issues_to_implement[:5]:  # Show first 5
                print(f"  - Issue #{issue.get('iid')}: {issue.get('title', 'Unknown')}")
            
            # Implement each issue with retry logic and checkpointing
            for idx, issue in enumerate(issues_to_implement, 1):
                issue_id = issue.get('iid')
                
                # Skip if already completed in previous run
                if any((c.get('iid') if isinstance(c, dict) else c) == issue_id for c in self.completed_issues):
                    print(f"\n[SKIP] Issue #{issue_id} already completed in previous run")
                    continue
                
                print(f"\n[PROGRESS] {idx}/{len(issues_to_implement)}")
                
                # Use retry logic for resilience
                success = await self.implement_issue(issue)  # Now has retry built-in
                
                if success:
                    self.completed_issues.append(issue)
                    issue_id = issue.get('iid') or issue.get('id') or 'Unknown'
                    print(f"[SUCCESS] ✅ Issue #{issue_id} completed successfully")
                else:
                    self.failed_issues.append(issue)
                    issue_id = issue.get('iid') or issue.get('id') or 'Unknown'
                    print(f"[WARNING] ❌ Issue #{issue_id} failed after {self.max_retries} attempts")
                
                # Checkpoint removed
                
                # Brief pause between issues
                if idx < len(issues_to_implement):
                    print("\n[PAUSE] 3 seconds between issues...")
                    await asyncio.sleep(3)
        
        # Phase 3: Final state and summary
        self.state = ExecutionState.COMPLETING
        
        # Execution complete
        
        # Show comprehensive summary
        await self._show_summary()
        
        # Set final state
        if len(self.failed_issues) == 0 and len(self.completed_issues) > 0:
            self.state = ExecutionState.COMPLETED
            print("\n✅ ORCHESTRATION COMPLETED SUCCESSFULLY")
        elif len(self.completed_issues) > 0:
            self.state = ExecutionState.COMPLETED
            print("\n⚠️ ORCHESTRATION COMPLETED WITH SOME FAILURES")
        else:
            self.state = ExecutionState.FAILED
            print("\n❌ ORCHESTRATION FAILED")
        
        # Clean up MCP client
        await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources managed by the supervisor."""
        # Execution finalized
        
        if self.client:
            await self.client.close()
    
    async def _show_summary(self):
        """Show enhanced execution summary with detailed metrics"""
        print("\n" + "="*70)
        print("ENHANCED EXECUTION SUMMARY")
        print("="*70)
        
        # Show issue implementation results
        total_issues = len(self.completed_issues) + len(self.failed_issues)
        if total_issues > 0:
            success_rate = (len(self.completed_issues) / total_issues) * 100
            print(f"\n📊 ISSUE IMPLEMENTATION:")
            print(f"  Total Processed: {total_issues}")
            print(f"  ✅ Completed: {len(self.completed_issues)}")
            print(f"  ❌ Failed: {len(self.failed_issues)}")
            print(f"  📈 Success Rate: {success_rate:.1f}%")
            
            if self.completed_issues:
                print(f"\n✅ Completed Issues:")
                for issue in self.completed_issues[:5]:
                    print(f"    - #{issue.get('iid')}: {issue.get('title', 'Unknown')}")
            
            if self.failed_issues:
                print(f"\n❌ Failed Issues:")
                for issue in self.failed_issues[:5]:
                    print(f"    - #{issue.get('iid')}: {issue.get('title', 'Unknown')}")
        
        # Generate and display summary report
        summary = self.performance_tracker.get_performance_summary()
        print(f"\n{summary}")
        
        # Show performance metrics
        perf_summary = self.performance_tracker.get_performance_summary()
        print(f"\n[PERFORMANCE] {perf_summary}")
        
        # Show execution statistics
        exec_summary = self.executor.get_execution_summary()
        print(f"[EXECUTION] {exec_summary}")
        
        # Show final state
        print(f"\n[FINAL STATE] {self.state.value}")

        # Summary complete
    
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

    async def _apply_planning_prioritization(self, all_issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply planning agent's prioritization and filter out completed issues.
        """
        print("[PLANNING] Applying planning agent's prioritization...")

        # Extract prioritized issue order from planning agent's analysis
        prioritized_issues = []

        # Get the planning agent's current plan/analysis
        planning_result = getattr(self.executor, 'current_plan', None)

        # Also check if we have our own plan stored
        if not planning_result and hasattr(self, 'current_plan'):
            planning_result = self.current_plan

        if planning_result:
            print("[PLANNING] Using planning agent's analysis for prioritization")
            # Extract issue order from planning text (if available)
            prioritized_issues = self._extract_issue_priority_from_plan(planning_result, all_issues)

        if not prioritized_issues:
            print("[PLANNING] No specific prioritization found, using dependency-based ordering")
            # Fallback: Use dependency-based prioritization
            prioritized_issues = self._apply_dependency_based_prioritization(all_issues)

        # Filter out completed/merged issues
        filtered_issues = []
        for issue in prioritized_issues:
            if await self._is_issue_completed(issue):
                issue_id = issue.get('iid') or issue.get('id')
                print(f"[SKIP] Issue #{issue_id} already completed/merged")
                continue
            filtered_issues.append(issue)

        return filtered_issues

    def _extract_issue_priority_from_plan(self, plan_data: Any, all_issues: List[Dict]) -> List[Dict]:
        """
        Extract issue priority order from planning agent's analysis.
        """
        if isinstance(plan_data, str):
            # Parse text-based plan for issue priorities
            return self._parse_text_plan_priorities(plan_data, all_issues)
        elif isinstance(plan_data, dict) and 'issues' in plan_data:
            # Use structured plan format
            return self._parse_structured_plan_priorities(plan_data, all_issues)
        else:
            return []

    def _parse_text_plan_priorities(self, plan_text: str, all_issues: List[Dict]) -> List[Dict]:
        """
        Parse text-based planning output for issue priorities.
        """
        prioritized = []
        issue_map = {str(issue.get('iid')): issue for issue in all_issues}

        # Look for priority patterns in the planning text
        import re

        # Pattern 1: "Phase 1: Issues #1, #5"
        phase_pattern = r'Phase \d+.*?Issue[s]?\s*[#:]?\s*([#\d,\s]+)'
        phases = re.findall(phase_pattern, plan_text, re.IGNORECASE)

        for phase in phases:
            # Extract issue numbers from each phase
            issue_numbers = re.findall(r'#?(\d+)', phase)
            for num in issue_numbers:
                if num in issue_map and issue_map[num] not in prioritized:
                    prioritized.append(issue_map[num])

        # Pattern 2: "Issue #X" mentions in order
        if not prioritized:
            issue_mentions = re.findall(r'Issue #(\d+)', plan_text)
            for num in issue_mentions:
                if num in issue_map and issue_map[num] not in prioritized:
                    prioritized.append(issue_map[num])

        # Add any remaining issues not mentioned in the plan
        for issue in all_issues:
            if issue not in prioritized:
                prioritized.append(issue)

        return prioritized

    def _parse_structured_plan_priorities(self, plan_data: Dict, all_issues: List[Dict]) -> List[Dict]:
        """
        Parse structured plan format for issue priorities.
        """
        prioritized = []
        issue_map = {str(issue.get('iid')): issue for issue in all_issues}

        if 'issues' in plan_data:
            for planned_issue in plan_data['issues']:
                issue_id = str(planned_issue.get('id') or planned_issue.get('iid', ''))
                if issue_id in issue_map:
                    prioritized.append(issue_map[issue_id])

        # Add any remaining issues
        for issue in all_issues:
            if issue not in prioritized:
                prioritized.append(issue)

        return prioritized

    def _apply_dependency_based_prioritization(self, all_issues: List[Dict]) -> List[Dict]:
        """
        Apply dependency-based prioritization as fallback.
        Based on common patterns: foundation issues first, then dependent features.
        """
        foundation_keywords = ['project', 'user', 'login', 'setup', 'database', 'model']
        feature_keywords = ['task', 'display', 'overview', 'form', 'list']
        ui_keywords = ['color', 'style', 'display', 'interface', 'gui']

        foundation_issues = []
        feature_issues = []
        ui_issues = []
        other_issues = []

        for issue in all_issues:
            title = issue.get('title', '').lower()
            description = issue.get('description', '').lower()
            text = f"{title} {description}"

            if any(keyword in text for keyword in foundation_keywords):
                foundation_issues.append(issue)
            elif any(keyword in text for keyword in ui_keywords):
                ui_issues.append(issue)
            elif any(keyword in text for keyword in feature_keywords):
                feature_issues.append(issue)
            else:
                other_issues.append(issue)

        # Return in dependency order: foundation → features → UI → others
        return foundation_issues + feature_issues + other_issues + ui_issues

    async def _is_issue_completed(self, issue: Dict[str, Any]) -> bool:
        """
        Check if an issue has already been completed/merged.
        Enhanced with better completion detection to avoid retry loops.
        """
        issue_id = issue.get('iid') or issue.get('id')
        if not issue_id:
            return False

        try:
            # Check if issue is closed
            if issue.get('state') == 'closed':
                print(f"[CHECK] Issue #{issue_id} is closed - marking as completed")
                return True

            # Check if there's already a merged branch for this issue
            branch_pattern = f"feature/issue-{issue_id}-"

            # Get list of branches
            list_branches_tool = None
            for tool in self.tools:
                if hasattr(tool, 'name') and tool.name == 'list_branches':
                    list_branches_tool = tool
                    break

            if list_branches_tool:
                branches_response = await list_branches_tool.ainvoke({
                    "project_id": self.project_id
                })

                if isinstance(branches_response, str):
                    import json
                    try:
                        branches = json.loads(branches_response)
                        if isinstance(branches, list):
                            # Check if feature branch exists (might indicate work in progress)
                            for branch in branches:
                                branch_name = branch.get('name', '')
                                if branch_name.startswith(branch_pattern):
                                    # Branch exists, but check if it's been merged
                                    print(f"[CHECK] Found branch {branch_name} for issue #{issue_id}")
                                    return False  # Work in progress, don't skip
                    except json.JSONDecodeError:
                        pass

            # Check merge requests for this issue
            list_mrs_tool = None
            for tool in self.tools:
                if hasattr(tool, 'name') and tool.name == 'list_merge_requests':
                    list_mrs_tool = tool
                    break

            if list_mrs_tool:
                mrs_response = await list_mrs_tool.ainvoke({
                    "project_id": self.project_id,
                    "state": "merged"
                })

                if isinstance(mrs_response, str):
                    import json
                    try:
                        mrs = json.loads(mrs_response)
                        if isinstance(mrs, list):
                            for mr in mrs:
                                mr_title = mr.get('title', '').lower()
                                mr_description = mr.get('description', '').lower()
                                source_branch = mr.get('source_branch', '')

                                # Check if MR mentions this issue or uses issue branch pattern
                                if (f"#{issue_id}" in mr_title or
                                    f"#{issue_id}" in mr_description or
                                    f"issue-{issue_id}" in source_branch or
                                    f"closes #{issue_id}" in mr_description):
                                    print(f"[CHECK] Issue #{issue_id} already merged in MR: {mr.get('title')}")
                                    return True
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            print(f"[CHECK] Error checking completion status for issue #{issue_id}: {e}")

        return False

    async def _execute_planning_with_retry(self, apply_changes: bool) -> bool:
        """Execute planning agent with retry logic."""
        for attempt in range(self.max_retries):
            if attempt > 0:
                print(f"[RETRY] Planning attempt {attempt + 1}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay * attempt)
            
            try:
                success = await self.route_task("planning", apply=apply_changes)
                if success:
                    return True
            except Exception as e:
                print(f"[PLANNING] Attempt {attempt + 1} failed: {e}")
        
        return False
    
    async def _fetch_gitlab_issues_via_mcp(self) -> List[Dict[str, Any]]:
        """
        Fetch issues from GitLab using MCP tools.
        This is used to sync with the orchestration plan if needed.
        """
        try:
            list_issues_tool = None
            for tool in self.tools:
                if hasattr(tool, 'name') and tool.name == 'list_issues':
                    list_issues_tool = tool
                    break
            
            if not list_issues_tool:
                print("[MCP] ⚠️ list_issues tool not found")
                return []
            
            print("[MCP] Fetching issues via MCP server...")
            response = await list_issues_tool.ainvoke({
                "project_id": self.project_id,
                "state": "opened"
            })
            
            if isinstance(response, str):
                try:
                    issues = json.loads(response)
                    if isinstance(issues, list):
                        print(f"[MCP] ✅ Fetched {len(issues)} issues")
                        return issues
                except json.JSONDecodeError:
                    print("[MCP] ⚠️ Could not parse issues response")
            elif isinstance(response, list):
                print(f"[MCP] ✅ Fetched {len(response)} issues")
                return response
            
            return []
            
        except Exception as e:
            print(f"[MCP] ❌ Failed to fetch issues: {e}")
            return []
    
    async def _update_orchestration_plan_for_completed_issue(self, issue: Dict[str, Any]):
        """
        Track completed issue (simplified - no longer maintains orchestration plans).
        """
        # Simply track completion - orchestration plans are deprecated
        issue_id = issue.get('iid') or issue.get('id')
        self.completed_issues.append(issue)  # Store full issue object
        total = len(self.gitlab_issues) if self.gitlab_issues else 0
        completed = len(self.completed_issues)

        if total > 0:
            print(f"[PROGRESS] Issue #{issue_id} completed ({completed}/{total} done)")
    
    async def _analyze_and_fix_pipeline_failures(self, issue_id: str):
        """
        Analyze CI/CD pipeline failures and provide debugging guidance.
        """
        try:
            # Get latest pipeline status
            pipeline_info = await self._get_latest_pipeline_status()
            if not pipeline_info:
                return
            
            status = pipeline_info.get("status", "unknown")
            if status != "success":
                print(f"\n[PIPELINE] Issue #{issue_id} - Status: {status}")
                
                # Get failed job details
                output = pipeline_info.get("output", "")
                if "FAILED" in output or "ERROR" in output:
                    print(f"[PIPELINE] Tests or build failed - agents will need to debug")
                    
                    # Store context for agents
                    self.executor.debugging_context = {
                        "issue_id": issue_id,
                        "pipeline_status": status,
                        "output": output[:1000]  # First 1000 chars for context
                    }
        except Exception as e:
            print(f"[PIPELINE] Could not analyze pipeline: {e}")
    
    async def _check_pipeline_status(self, issue_id: str):
        """
        Check pipeline status before finalizing implementation.
        """
        try:
            print(f"[PIPELINE] Checking status for issue #{issue_id}")
            
            # Get latest pipeline status
            pipeline_info = await self._get_latest_pipeline_status()
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
    
    async def _get_latest_pipeline_status(self) -> Optional[Dict]:
        """
        Get the latest CI/CD pipeline status and output.
        """
        try:
            # Find get_pipelines tool
            get_pipelines_tool = None
            for tool in self.tools:
                if hasattr(tool, 'name') and tool.name == 'get_pipelines':
                    get_pipelines_tool = tool
                    break
            
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
                get_jobs_tool = None
                for tool in self.tools:
                    if hasattr(tool, 'name') and tool.name == 'get_pipeline_jobs':
                        get_jobs_tool = tool
                        break
                
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
                            get_trace_tool = None
                            for tool in self.tools:
                                if hasattr(tool, 'name') and tool.name == 'get_job_trace':
                                    get_trace_tool = tool
                                    break
                            
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
        tech_stack: Technology stack preferences
    """
    supervisor = Supervisor(project_id, tech_stack=tech_stack)

    # Map mode to supervisor execution mode
    exec_mode = "implement" if mode == "implement" else "analyze"

    await supervisor.execute(mode=exec_mode, specific_issue=specific_issue)