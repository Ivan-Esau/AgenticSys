"""
Helper utilities for issue handling.

Provides standardized functions for extracting issue information from GitLab API responses
and ensuring consistent variable naming across the codebase.
"""

from typing import Dict, Any, Optional


def get_issue_iid(issue: Dict[str, Any]) -> Optional[int]:
    """
    Extract issue IID (project-specific internal ID).

    GitLab uses 'iid' (internal ID) for issues within a project,
    but some responses may use 'id' (global ID). Always prefer 'iid' when available.

    Args:
        issue: Issue dictionary from GitLab API

    Returns:
        Issue IID if found, None otherwise

    Example:
        >>> issue = {'iid': 123, 'title': 'Fix bug'}
        >>> get_issue_iid(issue)
        123
    """
    return issue.get('iid') or issue.get('id')


def get_issue_title(issue: Dict[str, Any]) -> str:
    """
    Extract issue title with safe default.

    Args:
        issue: Issue dictionary from GitLab API

    Returns:
        Issue title or 'Unknown' if not found

    Example:
        >>> issue = {'iid': 123, 'title': 'Fix bug'}
        >>> get_issue_title(issue)
        'Fix bug'
    """
    return issue.get('title', 'Unknown')


def get_issue_state(issue: Dict[str, Any]) -> str:
    """
    Extract issue state with safe default.

    Args:
        issue: Issue dictionary from GitLab API

    Returns:
        Issue state ('opened', 'closed', etc.) or 'unknown' if not found

    Example:
        >>> issue = {'iid': 123, 'state': 'closed'}
        >>> get_issue_state(issue)
        'closed'
    """
    return issue.get('state', 'unknown')


def validate_issue_structure(issue: Dict[str, Any]) -> bool:
    """
    Validate that an issue dictionary has the required fields.

    Args:
        issue: Issue dictionary to validate

    Returns:
        True if issue has required fields (iid and title), False otherwise

    Example:
        >>> valid_issue = {'iid': 123, 'title': 'Fix bug'}
        >>> validate_issue_structure(valid_issue)
        True
        >>> invalid_issue = {'title': 'Fix bug'}
        >>> validate_issue_structure(invalid_issue)
        False
    """
    if not isinstance(issue, dict):
        return False

    # Check for issue ID (either iid or id)
    has_id = ('iid' in issue) or ('id' in issue)
    has_title = 'title' in issue

    return has_id and has_title


def extract_issue_iid_from_branch(branch_name: str) -> Optional[int]:
    """
    Extract issue IID from a feature branch name.

    Supports branch naming patterns like:
    - feature/issue-123-description
    - feature/issue-123
    - issue-123-description

    Args:
        branch_name: Feature branch name

    Returns:
        Issue IID if found, None otherwise

    Example:
        >>> extract_issue_iid_from_branch('feature/issue-123-fix-bug')
        123
        >>> extract_issue_iid_from_branch('feature/issue-456')
        456
        >>> extract_issue_iid_from_branch('master')
        None
    """
    import re

    # Pattern: issue-<number>
    match = re.search(r'issue-(\d+)', branch_name)
    if match:
        return int(match.group(1))

    return None


def create_feature_branch_name(issue_iid: int, issue_title: str) -> str:
    """
    Create a standardized feature branch name from issue details.

    Args:
        issue_iid: Issue IID (project-specific internal ID)
        issue_title: Issue title

    Returns:
        Feature branch name in format: feature/issue-<iid>-<slug>

    Example:
        >>> create_feature_branch_name(123, 'Fix authentication bug')
        'feature/issue-123-fix-authentication-bug'
    """
    import re

    # Clean the title: remove special chars, replace spaces with hyphens
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', issue_title).lower()
    slug = re.sub(r'\s+', '-', slug).strip('-')[:30]  # Limit to 30 chars

    return f"feature/issue-{issue_iid}-{slug}"
