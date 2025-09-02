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
from .performance import PerformanceTracker
from .router import Router
from .agent_executor import AgentExecutor
from .pipeline_config import PipelineConfig


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
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.tools = None
        self.client = None
        self.default_branch = "master"
        self.current_plan = None
        self.state = ExecutionState.INITIALIZING
        
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
        self.executor = AgentExecutor(project_id, None, [])
        self.performance_tracker = PerformanceTracker()
        self.min_coverage = 70.0  # Minimum test coverage requirement
        self.pipeline_config = None  # Will be initialized after tech stack detection
        
        # Checkpoint directory
        self.checkpoint_dir = Path(".checkpoints")
        self.checkpoint_dir.mkdir(exist_ok=True)
    
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
        """Initialize pipeline configuration based on project tech stack."""
        try:
            # Try to detect tech stack from project files
            tech_stack = await self._detect_project_tech_stack()
            
            # Initialize pipeline config
            self.pipeline_config = PipelineConfig(tech_stack)
            
            print(f"[PIPELINE CONFIG] Initialized for {tech_stack.get('backend', 'unknown')} backend")
            if tech_stack.get('frontend') != 'none':
                print(f"[PIPELINE CONFIG] Frontend: {tech_stack.get('frontend')}")
            
            # Store config in executor for agents to use
            self.executor.pipeline_config = self.pipeline_config
            
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
            print(f"[ERROR] {routing_result['agent']}: {e}")
            
            print(f"[SUPERVISOR] ❌ Agent coordination failed: {e}")
            raise Exception(f"Task {task_type} failed: {e}")
    
    async def implement_issue(self, issue: Dict) -> bool:
        """
        Implement a single issue using the modular issue manager.
        """
        issue_id = issue.get("iid")
        issue_title = issue.get("title", "Unknown")
        
        # Validate issue structure
        if not self._validate_issue(issue):
            print(f"[ERROR] Invalid issue structure for #{issue_id}")
            return False
        
        print(f"\n[ISSUE #{issue_id}] Starting: {issue_title}")
        
        # Log issue implementation start
        print(f"[ISSUE #{issue_id}] Implementation starting")
        
        # Implement issue through agent pipeline
        try:
            # Phase 1: Coding with pipeline config
            print(f"[ISSUE #{issue_id}] Phase 1/3: Coding...")
            coding_result = await self.route_task(
                "coding",
                issue=issue,
                branch=self.default_branch
            )
            
            if not coding_result:
                print(f"[ISSUE #{issue_id}] ❌ Coding phase failed")
                return False
            
            # Phase 2: Testing with quality validation
            print(f"[ISSUE #{issue_id}] Phase 2/3: Testing...")
            
            # Log testing phase
            print(f"[ISSUE #{issue_id}] Running tests with minimum {self.min_coverage}% coverage requirement")
            
            testing_result = await self.route_task(
                "testing",
                issue=issue,
                branch=self.default_branch
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
                branch=self.default_branch
            )
            
            result = review_result
            
            if result:
                print(f"[ISSUE #{issue_id}] ✅ Successfully implemented")
                # Update orchestration plan
                await self._update_orchestration_plan_for_completed_issue(str(issue_id))
                
        except Exception as e:
            print(f"[ISSUE #{issue_id}] ❌ Implementation failed: {e}")
            result = False
        
        # Record final status
        final_status = "complete" if result else "failed"
        # Issue processing completed: {final_status}
        
        # Update orchestration plan if issue was completed successfully
        if result:
            await self._update_orchestration_plan_for_completed_issue(issue_id)
        
        return result
    
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
        
        # Load checkpoint if resuming
        if resume:
            await self._load_checkpoint()
        
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
        
        if not self.current_plan:
            # Need to run planning with retry logic
            success = await self._execute_planning_with_retry(apply_changes)
            if not success:
                print("[ERROR] Planning failed after retries")
                print("[ERROR] Planning phase failed")
                self.state = ExecutionState.FAILED
                return
        else:
            print("[CACHED] Using existing plan")
            # Ensure plan is normalized
            if self.executor.current_plan:
                self.current_plan = self.executor.current_plan
        
        if mode == "analyze":
            print("\n[COMPLETE] Analysis done. Run with --apply to implement.")
            self.state = ExecutionState.COMPLETED
            await self._show_summary()
            return
        
        # Phase 2: Implementation - Use issues from the orchestration plan
        print("\n" + "="*60)
        print("PHASE 2: IMPLEMENTATION PREPARATION")
        print("="*60)
        
        # The planning agent should have created a proper plan with issues
        # The executor normalizes the plan format, so we should have issues now
        if self.current_plan and self.current_plan.get("issues"):
            issues = self.current_plan.get("issues", [])
            print(f"[ISSUES] Found {len(issues)} issues in orchestration plan")
            
            # Show issue details
            for issue in issues[:5]:  # Show first 5
                status = issue.get('implementation_status', 'pending')
                print(f"  - Issue #{issue.get('iid')}: {issue.get('title')} [{status}]")
        else:
            print("[ISSUES] No issues found in orchestration plan")
            print("[DEBUG] Plan keys:", list(self.current_plan.keys()) if self.current_plan else "No plan")
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
                    print(f"[ERROR] Issue {specific_issue} not found")
                    return
            else:
                # All issues mode - filter out already completed
                issues_to_implement = []
                for issue in issues:
                    status = issue.get("implementation_status", "pending")
                    if status != "complete" and status != "completed":
                        issues_to_implement.append(issue)
                
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
                if any(c.get('iid') == issue_id for c in self.completed_issues):
                    print(f"\n[SKIP] Issue #{issue_id} already completed in previous run")
                    continue
                
                print(f"\n[PROGRESS] {idx}/{len(issues_to_implement)}")
                
                # Use retry logic for resilience
                success = await self._implement_issue_with_retry(issue)
                
                if success:
                    self.completed_issues.append(issue)
                    print(f"[SUCCESS] ✅ Issue #{issue['iid']} completed successfully")
                else:
                    self.failed_issues.append(issue)
                    print(f"[WARNING] ❌ Issue #{issue['iid']} failed after {self.max_retries} attempts")
                
                # Save checkpoint after each issue
                await self._save_checkpoint()
                
                # Brief pause between issues
                if idx < len(issues_to_implement):
                    print("\n[PAUSE] 3 seconds between issues...")
                    await asyncio.sleep(3)
        
        # Phase 3: Final state and summary
        self.state = ExecutionState.COMPLETING
        
        # Final checkpoint save
        await self._save_checkpoint()
        
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
        
        # Checkpoint info
        checkpoint_file = self.checkpoint_dir / f"supervisor_{self.project_id}.json"
        if checkpoint_file.exists():
            print(f"[CHECKPOINT] State saved - can resume with --resume flag")
    
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
    
    async def _sync_plan_with_gitlab_issues(self):
        """
        Optionally sync the orchestration plan with current GitLab issues.
        This can be used to update issue states if needed.
        """
        if not self.current_plan:
            return
        
        gitlab_issues = await self._fetch_gitlab_issues_via_mcp()
        if not gitlab_issues:
            return
        
        # Create mapping of GitLab issues
        gitlab_map = {str(i.get('iid')): i for i in gitlab_issues}
        
        # Update plan issues with current GitLab state
        for plan_issue in self.current_plan.get('issues', []):
            issue_id = str(plan_issue.get('iid'))
            if issue_id in gitlab_map:
                # Update state from GitLab
                gitlab_issue = gitlab_map[issue_id]
                plan_issue['state'] = gitlab_issue.get('state', 'opened')
                
                # Skip closed issues
                if gitlab_issue.get('state') == 'closed':
                    plan_issue['implementation_status'] = 'completed'
        
        print(f"[SYNC] Updated plan with GitLab issue states")
    
    async def _load_checkpoint(self):
        """Load execution checkpoint for recovery."""
        checkpoint_file = self.checkpoint_dir / f"supervisor_{self.project_id}.json"
        
        try:
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                
                self.completed_issues = checkpoint.get('completed_issues', [])
                self.failed_issues = checkpoint.get('failed_issues', [])
                self.state = ExecutionState(checkpoint.get('state', 'initializing'))
                
                print(f"[CHECKPOINT] Loaded - {len(self.completed_issues)} completed, {len(self.failed_issues)} failed")
                return True
        except Exception as e:
            print(f"[CHECKPOINT] Could not load: {e}")
        
        return False
    
    async def _save_checkpoint(self):
        """Save execution checkpoint for recovery."""
        checkpoint_file = self.checkpoint_dir / f"supervisor_{self.project_id}.json"
        
        checkpoint = {
            'project_id': self.project_id,
            'state': self.state.value,
            'completed_issues': self.completed_issues,
            'failed_issues': self.failed_issues,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            print("[CHECKPOINT] Saved execution state")
        except Exception as e:
            print(f"[CHECKPOINT] Could not save: {e}")
    
    async def _implement_issue_with_retry(self, issue: Dict) -> bool:
        """
        Implement issue with retry logic for resilience.
        """
        issue_id = issue.get('iid')
        
        for attempt in range(self.max_retries):
            if attempt > 0:
                print(f"[RETRY] Issue #{issue_id} attempt {attempt + 1}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay * attempt)
            
            try:
                # Use existing issue manager for implementation
                success = await self.implement_issue(issue)
                if success:
                    return True
            except Exception as e:
                print(f"[ERROR] Issue #{issue_id} attempt {attempt + 1} failed: {e}")
        
        return False
    
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
            print(f"[ERROR] Plan update failed for issue #{issue_id}: {e}")
    
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
        tech_stack: Technology stack preferences (not used in simplified version)
    """
    supervisor = Supervisor(project_id)
    
    # Map mode to supervisor execution mode
    exec_mode = "implement" if mode == "implement" else "analyze"
    
    await supervisor.execute(mode=exec_mode, specific_issue=specific_issue)