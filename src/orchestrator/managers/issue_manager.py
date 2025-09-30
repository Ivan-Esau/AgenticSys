"""
Issue Management Module
Handles issue tracking, validation, implementation, and completion checking.
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Any


class IssueManager:
    """
    Manages GitLab issues including tracking, prioritization, and implementation.
    """

    def __init__(self, project_id: str, tools: List[Any]):
        self.project_id = project_id
        self.tools = tools

        # Issue tracking
        self.gitlab_issues = []
        self.implementation_queue = []
        self.completed_issues = []
        self.failed_issues = []

        # Current issue being processed
        self.current_issue_number = None
        self.current_issue_title = None

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 5

    def validate_issue(self, issue: Dict) -> bool:
        """Simple issue validation."""
        if not isinstance(issue, dict):
            print(f"[VALIDATION] Issue must be a dictionary")
            return False
        if "iid" not in issue or "title" not in issue:
            print(f"[VALIDATION] Issue missing required fields (iid or title)")
            return False
        return True

    def create_feature_branch_name(self, issue: Dict) -> str:
        """Create a feature branch name from issue details."""
        issue_id = issue.get('iid')
        issue_title = issue.get('title', '')

        # Clean the title: remove special chars, replace spaces with hyphens
        issue_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', issue_title).lower()
        issue_slug = re.sub(r'\s+', '-', issue_slug).strip('-')[:30]

        return f"feature/issue-{issue_id}-{issue_slug}"

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
            list_branches_tool = self._get_tool('list_branches')

            if list_branches_tool:
                branches_response = await list_branches_tool.ainvoke({
                    "project_id": self.project_id
                })

                if isinstance(branches_response, str):
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
            list_mrs_tool = self._get_tool('list_merge_requests')

            if list_mrs_tool:
                mrs_response = await list_mrs_tool.ainvoke({
                    "project_id": self.project_id,
                    "state": "merged"
                })

                if isinstance(mrs_response, str):
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

    def track_completed_issue(self, issue: Dict[str, Any]):
        """
        Track completed issue and show progress.
        """
        issue_id = issue.get('iid') or issue.get('id')
        self.completed_issues.append(issue)
        total = len(self.gitlab_issues) if self.gitlab_issues else 0
        completed = len(self.completed_issues)

        if total > 0:
            print(f"[PROGRESS] Issue #{issue_id} completed ({completed}/{total} done)")

    def track_failed_issue(self, issue: Dict[str, Any]):
        """
        Track failed issue.
        """
        issue_id = issue.get('iid') or issue.get('id')
        self.failed_issues.append(issue)
        print(f"[WARNING] Issue #{issue_id} failed after {self.max_retries} attempts")

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for issues.
        """
        total_issues = len(self.completed_issues) + len(self.failed_issues)
        success_rate = 0

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