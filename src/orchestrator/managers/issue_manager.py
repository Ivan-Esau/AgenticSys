"""
Issue Management Module
Handles issue tracking, validation, implementation, and completion checking.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any

from ..utils.issue_helpers import (
    get_issue_iid,
    get_issue_title,
    validate_issue_structure,
    create_feature_branch_name as create_branch_name
)


class IssueManager:
    """
    Manages GitLab issues including tracking, prioritization, and implementation.
    """

    def __init__(self, project_id: str, tools: List[Any]):
        self.project_id: str = project_id
        self.tools: List[Any] = tools

        # Issue tracking with proper type annotations
        self.gitlab_issues: List[Dict[str, Any]] = []
        self.implementation_queue: List[Dict[str, Any]] = []
        self.completed_issues: List[Dict[str, Any]] = []
        self.failed_issues: List[Dict[str, Any]] = []

        # Current issue being processed
        self.current_issue_number: Optional[int] = None
        self.current_issue_title: Optional[str] = None

        # Retry configuration
        self.max_retries: int = 3
        self.retry_delay: int = 5

    def validate_issue(self, issue: Dict[str, Any]) -> bool:
        """
        Simple issue validation using standardized helper.

        Args:
            issue: Issue dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        if not validate_issue_structure(issue):
            print(f"[VALIDATION] Issue missing required fields (iid/id or title)")
            return False
        return True

    def create_feature_branch_name(self, issue: Dict[str, Any]) -> str:
        """
        Create a feature branch name from issue details using standardized helper.

        Args:
            issue: Issue dictionary

        Returns:
            Feature branch name in format: feature/issue-<iid>-<slug>
        """
        issue_iid = get_issue_iid(issue)
        issue_title = get_issue_title(issue)

        if not issue_iid:
            raise ValueError("Issue must have an iid or id field")

        return create_branch_name(issue_iid, issue_title)

    async def fetch_gitlab_issues(self) -> List[Dict[str, Any]]:
        """
        Fetch issues from GitLab using MCP tools.
        """
        try:
            list_issues_tool = self._get_tool('list_issues')

            if not list_issues_tool:
                print("[MCP] [WARN] list_issues tool not found")
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
                        print(f"[MCP] Fetched {len(issues)} issues")
                        self.gitlab_issues = issues
                        return issues
                except json.JSONDecodeError:
                    print("[MCP] Could not parse issues response")
            elif isinstance(response, list):
                print(f"[MCP] Fetched {len(response)} issues")
                self.gitlab_issues = response
                return response

            return []

        except Exception as e:
            print(f"[MCP] Failed to fetch issues: {e}")
            return []

    async def is_issue_completed(self, issue: Dict[str, Any]) -> bool:
        """
        Check if an issue has already been completed/merged.

        CRITICAL: An issue is only "completed" if there's a MERGED MR for it.
        Issue state (open/closed) is NOT enough - the branch must be merged.
        """
        issue_iid = get_issue_iid(issue)
        issue_title = issue.get('title', 'Unknown')
        print(f"[COMPLETION-CHECK] Checking if issue #{issue_iid} ({issue_title}) is completed...")

        if not issue_iid:
            print(f"[COMPLETION-CHECK] Issue #{issue_iid}: No IID found - treating as NOT completed")
            return False

        try:
            # STEP 1: Check for merged MRs mentioning this issue
            print(f"[COMPLETION-CHECK] Issue #{issue_iid}: Step 1 - Checking for merged MRs...")
            list_mrs_tool = self._get_tool('list_merge_requests')

            if list_mrs_tool:
                mrs_response = await list_mrs_tool.ainvoke({
                    "project_id": self.project_id,
                    "state": "merged"  # Only check MERGED MRs
                })

                if isinstance(mrs_response, str):
                    try:
                        mrs = json.loads(mrs_response)
                        if isinstance(mrs, list):
                            print(f"[COMPLETION-CHECK] Issue #{issue_iid}: Found {len(mrs)} merged MRs to check")
                            for mr in mrs:
                                mr_title = mr.get('title', '').lower()
                                mr_description = mr.get('description', '').lower()
                                source_branch = mr.get('source_branch', '')

                                # Check if MR is for this issue
                                if (f"#{issue_iid}" in mr_title or
                                    f"#{issue_iid}" in mr_description or
                                    f"issue-{issue_iid}" in source_branch or
                                    f"closes #{issue_iid}" in mr_description):
                                    print(f"[COMPLETION-CHECK] Issue #{issue_iid}: [OK] COMPLETED - Found merged MR: {mr.get('title')}")
                                    print(f"[COMPLETION-CHECK] Issue #{issue_iid}: MR branch: {source_branch}")
                                    return True  # Found merged MR - truly completed
                            print(f"[COMPLETION-CHECK] Issue #{issue_iid}: No merged MRs found referencing this issue")
                    except json.JSONDecodeError:
                        print(f"[COMPLETION-CHECK] Issue #{issue_iid}: Failed to parse MRs response")
                        pass
                else:
                    print(f"[COMPLETION-CHECK] Issue #{issue_iid}: MRs response is not a string (type: {type(mrs_response)})")

            # STEP 2: No merged MR found - check if work is in progress
            # If issue is closed but no merged MR, the branch might still need merging!
            print(f"[COMPLETION-CHECK] Issue #{issue_iid}: Step 2 - Checking issue state...")
            issue_state = issue.get('state', 'unknown')
            print(f"[COMPLETION-CHECK] Issue #{issue_iid}: State is '{issue_state}'")

            if issue.get('state') == 'closed':
                print(f"[COMPLETION-CHECK] Issue #{issue_iid}: Issue is CLOSED but NO merged MR found")
                print(f"[COMPLETION-CHECK] Issue #{issue_iid}: Checking if feature branch exists...")

                # Check if feature branch exists
                branch_pattern = f"feature/issue-{issue_iid}-"
                list_branches_tool = self._get_tool('list_branches')

                if list_branches_tool:
                    branches_response = await list_branches_tool.ainvoke({
                        "project_id": self.project_id
                    })

                    if isinstance(branches_response, str):
                        try:
                            branches = json.loads(branches_response)
                            if isinstance(branches, list):
                                for branch in branches:
                                    branch_name = branch.get('name', '')
                                    if branch_name.startswith(branch_pattern):
                                        print(f"[CHECK] Found unmerged branch: {branch_name}")
                                        print(f"[CHECK] Issue #{issue_iid} needs review/merge - NOT completed")
                                        return False  # Branch exists unmerged - needs work!
                        except json.JSONDecodeError:
                            pass

                # Issue closed, no branch found, no merged MR
                # This is edge case - issue might have been closed without implementation
                print(f"[COMPLETION-CHECK] Issue #{issue_iid}: [OK] COMPLETED - Issue closed with no branch or MR")
                print(f"[COMPLETION-CHECK] Issue #{issue_iid}: Treating as completed (edge case)")
                return True
            else:
                # Issue is open - not completed
                print(f"[COMPLETION-CHECK] Issue #{issue_iid}: [X] NOT COMPLETED - Issue is open and no merged MR exists")
                return False

        except Exception as e:
            print(f"[COMPLETION-CHECK] Issue #{issue_iid}: ERROR during check: {e}")
            import traceback
            traceback.print_exc()

        # Default: Not completed
        print(f"[COMPLETION-CHECK] Issue #{issue_iid}: [X] NOT COMPLETED - Default (no evidence of completion)")
        return False

    def track_completed_issue(self, issue: Dict[str, Any]):
        """
        Track completed issue and show progress.

        Args:
            issue: Completed issue dictionary
        """
        issue_iid = get_issue_iid(issue)
        self.completed_issues.append(issue)
        total = len(self.gitlab_issues) if self.gitlab_issues else 0
        completed = len(self.completed_issues)

        if total > 0:
            print(f"[PROGRESS] Issue #{issue_iid} completed ({completed}/{total} done)")

    def track_failed_issue(self, issue: Dict[str, Any]):
        """
        Track failed issue.

        Args:
            issue: Failed issue dictionary
        """
        issue_iid = get_issue_iid(issue)
        self.failed_issues.append(issue)
        print(f"[WARNING] Issue #{issue_iid} failed after {self.max_retries} attempts")

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for issues.

        Returns:
            Dictionary with issue statistics
        """
        total_issues = len(self.completed_issues) + len(self.failed_issues)
        success_rate: float = 0.0  # Use float from the start

        if total_issues > 0:
            success_rate = (len(self.completed_issues) / total_issues) * 100

        return {
            'total_processed': total_issues,
            'completed': len(self.completed_issues),
            'failed': len(self.failed_issues),
            'success_rate': success_rate,
            'completed_issues': self.completed_issues[:5],  # First 5
            'failed_issues': self.failed_issues[:5]  # First 5
        }

    def _get_tool(self, tool_name: str):
        """Helper to get a tool by name."""
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
        return None